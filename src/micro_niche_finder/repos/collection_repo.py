from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from micro_niche_finder.domain.models import ApiUsageCounter, CollectionSchedule, QueryGroup


class CollectionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_schedule_for_query_group(self, query_group_id: int) -> CollectionSchedule | None:
        stmt = select(CollectionSchedule).where(CollectionSchedule.query_group_id == query_group_id)
        return self.session.scalar(stmt)

    def get_schedule_for_query_group_and_source(self, query_group_id: int, source: str) -> CollectionSchedule | None:
        stmt = select(CollectionSchedule).where(
            CollectionSchedule.query_group_id == query_group_id,
            CollectionSchedule.source == source,
        )
        return self.session.scalar(stmt)

    def upsert_schedule(
        self,
        *,
        query_group_id: int,
        source: str,
        priority: int,
        cadence_minutes: int,
        collection_targets_json: list[dict],
        next_collect_at: datetime,
    ) -> CollectionSchedule:
        schedule = self.get_schedule_for_query_group_and_source(query_group_id, source)
        if schedule:
            schedule.source = source
            schedule.priority = priority
            schedule.cadence_minutes = cadence_minutes
            schedule.collection_targets_json = collection_targets_json
            if not schedule.next_collect_at:
                schedule.next_collect_at = next_collect_at
            return schedule

        entity = CollectionSchedule(
            query_group_id=query_group_id,
            source=source,
            priority=priority,
            cadence_minutes=cadence_minutes,
            collection_targets_json=collection_targets_json,
            next_collect_at=next_collect_at,
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def list_due_schedules(self, *, source: str, now: datetime, limit: int) -> list[CollectionSchedule]:
        stmt = (
            select(CollectionSchedule)
            .where(CollectionSchedule.source == source)
            .where(CollectionSchedule.is_active.is_(True))
            .where(CollectionSchedule.next_collect_at <= now)
            .options(joinedload(CollectionSchedule.query_group))
            .order_by(CollectionSchedule.priority.desc(), CollectionSchedule.next_collect_at.asc(), CollectionSchedule.id.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).unique())

    def list_query_groups_without_schedule(self) -> list[QueryGroup]:
        stmt = (
            select(QueryGroup)
            .outerjoin(CollectionSchedule, CollectionSchedule.query_group_id == QueryGroup.id)
            .where(CollectionSchedule.id.is_(None))
            .order_by(QueryGroup.created_at.asc())
        )
        return list(self.session.scalars(stmt))

    def list_query_groups_without_schedule_for_source(self, source: str) -> list[QueryGroup]:
        stmt = (
            select(QueryGroup)
            .outerjoin(
                CollectionSchedule,
                (CollectionSchedule.query_group_id == QueryGroup.id) & (CollectionSchedule.source == source),
            )
            .options(joinedload(QueryGroup.problem_candidate))
            .where(CollectionSchedule.id.is_(None))
            .order_by(QueryGroup.created_at.asc())
        )
        return list(self.session.scalars(stmt).unique())

    def get_or_create_usage_counter(self, *, source: str, usage_date: date, daily_limit: int) -> ApiUsageCounter:
        stmt = select(ApiUsageCounter).where(ApiUsageCounter.source == source, ApiUsageCounter.usage_date == usage_date)
        counter = self.session.scalar(stmt)
        if counter:
            return counter
        counter = ApiUsageCounter(source=source, usage_date=usage_date, daily_limit=daily_limit, calls_made=0)
        self.session.add(counter)
        self.session.flush()
        return counter
