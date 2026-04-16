from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from micro_niche_finder.domain.schemas import CollectionTarget, CollectorRunSummary
from micro_niche_finder.repos.collection_repo import CollectionRepository
from micro_niche_finder.repos.trend_repo import TrendRepository
from micro_niche_finder.services.budget_allocator_service import BudgetAllocatorService
from micro_niche_finder.services.collection_scheduler_service import CollectionSchedulerService
from micro_niche_finder.services.datalab_service import NaverDataLabService
from micro_niche_finder.services.feature_service import FeatureExtractionService


class CollectorService:
    SOURCE = "naver_datalab"

    def __init__(
        self,
        *,
        datalab_service: NaverDataLabService,
        feature_service: FeatureExtractionService,
        budget_allocator: BudgetAllocatorService,
        collection_scheduler: CollectionSchedulerService,
    ) -> None:
        self.datalab_service = datalab_service
        self.feature_service = feature_service
        self.budget_allocator = budget_allocator
        self.collection_scheduler = collection_scheduler

    def run_once(self, *, session: Session, max_calls: int | None = None) -> CollectorRunSummary:
        now = datetime.now(timezone.utc)
        collection_repo = CollectionRepository(session)
        trend_repo = TrendRepository(session)

        counter = collection_repo.get_or_create_usage_counter(
            source=self.SOURCE,
            usage_date=now.date(),
            daily_limit=self.datalab_service.settings.naver_datalab_daily_limit,
        )
        allowance = self.budget_allocator.allowance_for_run(
            calls_made_today=counter.calls_made,
            now=now,
            max_calls=max_calls,
            daily_limit=self.datalab_service.settings.naver_datalab_daily_limit,
        )
        due_schedules = collection_repo.list_due_schedules(source=self.SOURCE, now=now, limit=allowance)

        processed = 0
        calls_made = 0
        errors: list[str] = []

        for schedule in due_schedules:
            targets = [CollectionTarget.model_validate(item) for item in schedule.collection_targets_json]
            if not targets or schedule.query_group is None:
                continue
            target = targets[schedule.next_target_index % len(targets)]

            try:
                request = self.datalab_service.build_request(
                    group_name=schedule.query_group.canonical_name,
                    queries=schedule.query_group.queries_json,
                    weeks=target.weeks,
                    time_unit=target.time_unit,
                    device=target.device,
                    ages=target.ages,
                    gender=target.gender,
                )
                response = self.datalab_service.fetch(request)
                trend_repo.create_snapshot(
                    query_group_id=schedule.query_group_id,
                    source=self.SOURCE,
                    window_start=datetime.combine(response.startDate, datetime.min.time(), tzinfo=timezone.utc),
                    window_end=datetime.combine(response.endDate, datetime.min.time(), tzinfo=timezone.utc),
                    target_key=target.key,
                    request_payload_json=request.model_dump(mode="json", exclude_none=True),
                    raw_response_json=response.model_dump(mode="json"),
                )
                if target.updates_features:
                    features = self.feature_service.extract(
                        response=response,
                        query_count=len(schedule.query_group.queries_json),
                        queries=schedule.query_group.queries_json,
                    )
                    trend_repo.upsert_feature(query_group_id=schedule.query_group_id, **features.model_dump())

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
                    minutes=min(360, schedule.cadence_minutes * max(1, schedule.failure_count))
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
