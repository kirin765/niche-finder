from datetime import datetime, timezone

from micro_niche_finder.services.budget_allocator_service import BudgetAllocatorService


def test_allowance_spreads_daily_budget() -> None:
    service = BudgetAllocatorService()
    now = datetime(2026, 4, 6, 0, 0, tzinfo=timezone.utc)
    allowance = service.allowance_for_run(calls_made_today=0, now=now)
    assert allowance >= 10
    assert allowance <= 11


def test_allowance_respects_max_calls_override() -> None:
    service = BudgetAllocatorService()
    now = datetime(2026, 4, 6, 12, 0, tzinfo=timezone.utc)
    allowance = service.allowance_for_run(calls_made_today=500, now=now, max_calls=3)
    assert allowance == 3


def test_allowance_returns_zero_when_budget_exhausted() -> None:
    service = BudgetAllocatorService()
    now = datetime(2026, 4, 6, 12, 0, tzinfo=timezone.utc)
    allowance = service.allowance_for_run(calls_made_today=1000, now=now)
    assert allowance == 0
