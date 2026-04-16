from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from micro_niche_finder.config.settings import get_settings


class BudgetAllocatorService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def allowance_for_run(
        self,
        *,
        calls_made_today: int,
        now: datetime | None = None,
        max_calls: int | None = None,
        daily_limit: int | None = None,
    ) -> int:
        current = now or datetime.now(timezone.utc)
        limit = daily_limit if daily_limit is not None else self.settings.naver_datalab_daily_limit
        remaining_budget = max(0, limit - calls_made_today)
        if remaining_budget == 0:
            return 0

        start_of_next_day = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_remaining = max(1, int((start_of_next_day - current).total_seconds()))
        interval_seconds = max(60, self.settings.collector_interval_minutes * 60)
        slots_remaining = max(1, math.ceil(seconds_remaining / interval_seconds))
        allowance = math.ceil(remaining_budget / slots_remaining)
        if max_calls is not None:
            allowance = min(allowance, max_calls)
        return max(0, allowance)
