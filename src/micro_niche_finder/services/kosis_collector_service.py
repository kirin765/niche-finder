from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from micro_niche_finder.domain.schemas import CollectionTarget, CollectorRunSummary, KosisIndustrySelection, KosisProfileRequest
from micro_niche_finder.repos.collection_repo import CollectionRepository
from micro_niche_finder.repos.trend_repo import TrendRepository
from micro_niche_finder.services.budget_allocator_service import BudgetAllocatorService
from micro_niche_finder.services.kosis_employee_service import KosisEmployeeService


class KosisCollectorService:
    SOURCE = KosisEmployeeService.SOURCE

    def __init__(
        self,
        *,
        kosis_employee_service: KosisEmployeeService,
        budget_allocator: BudgetAllocatorService,
    ) -> None:
        self.kosis_employee_service = kosis_employee_service
        self.budget_allocator = budget_allocator

    def run_once(self, *, session: Session, max_calls: int | None = None) -> CollectorRunSummary:
        now = datetime.now(timezone.utc)
        if not self.kosis_employee_service.is_configured():
            return CollectorRunSummary(
                source=self.SOURCE,
                run_started_at=now,
                allowance=0,
                schedules_considered=0,
                schedules_processed=0,
                calls_made=0,
                errors=[],
            )

        collection_repo = CollectionRepository(session)
        trend_repo = TrendRepository(session)

        counter = collection_repo.get_or_create_usage_counter(
            source=self.SOURCE,
            usage_date=now.date(),
            daily_limit=self.kosis_employee_service.settings.kosis_employee_daily_limit,
        )
        allowance = self.budget_allocator.allowance_for_run(
            calls_made_today=counter.calls_made,
            now=now,
            max_calls=max_calls,
        )
        due_schedules = collection_repo.list_due_schedules(source=self.SOURCE, now=now, limit=allowance)

        processed = 0
        calls_made = 0
        errors: list[str] = []

        for schedule in due_schedules:
            targets = [CollectionTarget.model_validate(item) for item in schedule.collection_targets_json]
            if not targets:
                continue
            target = targets[schedule.next_target_index % len(targets)]

            try:
                if "profile_name" in target.metadata:
                    request = KosisProfileRequest.model_validate(target.metadata)
                    response = self.kosis_employee_service.fetch_profile(request)
                    window_start = datetime(response.start_year, 1, 1, tzinfo=timezone.utc)
                    window_end = datetime(response.end_year, 12, 31, tzinfo=timezone.utc)
                    payload = response.model_dump(mode="json")
                else:
                    selection = KosisIndustrySelection.model_validate(target.metadata)
                    legacy_request = self.kosis_employee_service.build_request(selection)
                    legacy_response = self.kosis_employee_service.fetch(legacy_request)
                    window_start = datetime(legacy_response.reference_year, 1, 1, tzinfo=timezone.utc)
                    window_end = datetime(legacy_response.reference_year, 12, 31, tzinfo=timezone.utc)
                    payload = legacy_response.model_dump(mode="json")
                trend_repo.create_snapshot(
                    query_group_id=schedule.query_group_id,
                    source=self.SOURCE,
                    window_start=window_start,
                    window_end=window_end,
                    target_key=target.key,
                    request_payload_json=(
                        request.model_dump(mode="json") if "profile_name" in target.metadata else legacy_request.model_dump(mode="json")
                    ),
                    raw_response_json=payload,
                )

                schedule.last_collected_at = now
                schedule.next_collect_at = now + timedelta(minutes=schedule.cadence_minutes)
                schedule.next_target_index = (schedule.next_target_index + 1) % len(targets)
                schedule.last_status = "success"
                schedule.failure_count = 0
                schedule.last_error = None
                counter.calls_made += 1
                processed += 1
                calls_made += 1
            except Exception as exc:
                schedule.last_status = "error"
                schedule.failure_count += 1
                schedule.last_error = str(exc)[:1000]
                schedule.next_collect_at = now + timedelta(
                    minutes=min(1440, schedule.cadence_minutes * max(1, schedule.failure_count))
                )
                errors.append(f"schedule={schedule.id} target={target.key}: {exc}")

        return CollectorRunSummary(
            source=self.SOURCE,
            run_started_at=now,
            allowance=allowance,
            schedules_considered=len(due_schedules),
            schedules_processed=processed,
            calls_made=calls_made,
            errors=errors,
        )
