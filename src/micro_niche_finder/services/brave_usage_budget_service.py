from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import update

from micro_niche_finder.config.database import Base, SessionLocal, engine
from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.models import ApiUsageCounter
from micro_niche_finder.repos.collection_repo import CollectionRepository


class BraveUsageBudgetService:
    SOURCE = "brave_search_web_monthly"

    def __init__(self) -> None:
        self.settings = get_settings()
        Base.metadata.create_all(bind=engine, tables=[ApiUsageCounter.__table__])

    @staticmethod
    def _month_start(current: datetime) -> date:
        return date(current.year, current.month, 1)

    def remaining_monthly_calls(self, *, now: datetime | None = None) -> int:
        current = now or datetime.now(timezone.utc)
        try:
            with SessionLocal() as session:
                repo = CollectionRepository(session)
                counter = repo.get_or_create_usage_counter(
                    source=self.SOURCE,
                    usage_date=self._month_start(current),
                    daily_limit=self.settings.brave_search_monthly_limit,
                )
                if counter.daily_limit != self.settings.brave_search_monthly_limit:
                    counter.daily_limit = self.settings.brave_search_monthly_limit
                session.commit()
                return max(0, counter.daily_limit - counter.calls_made)
        except Exception:
            return 0

    def consume_monthly_call(self, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        try:
            with SessionLocal() as session:
                repo = CollectionRepository(session)
                counter = repo.get_or_create_usage_counter(
                    source=self.SOURCE,
                    usage_date=self._month_start(current),
                    daily_limit=self.settings.brave_search_monthly_limit,
                )
                if counter.daily_limit != self.settings.brave_search_monthly_limit:
                    counter.daily_limit = self.settings.brave_search_monthly_limit
                session.flush()
                result = session.execute(
                    update(ApiUsageCounter)
                    .where(ApiUsageCounter.id == counter.id)
                    .where(ApiUsageCounter.calls_made < ApiUsageCounter.daily_limit)
                    .values(calls_made=ApiUsageCounter.calls_made + 1)
                )
                if result.rowcount == 0:
                    session.commit()
                    return False
                session.commit()
                return True
        except Exception:
            return False
