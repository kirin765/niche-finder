from __future__ import annotations

from datetime import datetime, timedelta, timezone

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import (
    CollectionTarget,
    KosisProfileRequest,
    NaverShoppingCategorySelection,
)


class CollectionSchedulerService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def default_targets(self) -> list[CollectionTarget]:
        return [
            CollectionTarget(key="baseline_12w", weeks=12, updates_features=True),
            CollectionTarget(key="baseline_12w_refresh", weeks=12, updates_features=True),
            CollectionTarget(key="baseline_26w", weeks=26),
            CollectionTarget(key="baseline_52w", weeks=52),
            CollectionTarget(key="device_mobile_12w", weeks=12, device="mo"),
            CollectionTarget(key="device_pc_12w", weeks=12, device="pc"),
            CollectionTarget(key="gender_m_12w", weeks=12, gender="m"),
            CollectionTarget(key="gender_f_12w", weeks=12, gender="f"),
            CollectionTarget(key="age_20_12w", weeks=12, ages=["20"]),
            CollectionTarget(key="age_30_12w", weeks=12, ages=["30"]),
            CollectionTarget(key="age_40_12w", weeks=12, ages=["40"]),
            CollectionTarget(key="age_50_12w", weeks=12, ages=["50"]),
            CollectionTarget(key="age_60_12w", weeks=12, ages=["60"]),
        ]

    def google_default_targets(self, query_count: int) -> list[CollectionTarget]:
        target_count = min(3, max(1, query_count))
        return [
            CollectionTarget(
                key=f"google_query_{index}",
                weeks=0,
                metadata={"query_index": index},
            )
            for index in range(target_count)
        ]

    def naver_search_default_targets(self, query_count: int) -> list[CollectionTarget]:
        target_count = min(3, max(1, query_count))
        return [
            CollectionTarget(
                key=f"naver_search_query_{index}",
                weeks=0,
                metadata={"query_index": index},
            )
            for index in range(target_count)
        ]

    def kosis_default_targets(self, requests: list[KosisProfileRequest]) -> list[CollectionTarget]:
        return [
            CollectionTarget(
                key=f"kosis_{request.profile_name}_{request.metric_key}_{request.start_year}_{request.end_year}",
                weeks=0,
                metadata=request.model_dump(mode="json"),
            )
            for request in requests
        ]

    def naver_shopping_default_targets(self, selection: NaverShoppingCategorySelection) -> list[CollectionTarget]:
        return [
            CollectionTarget(
                key="naver_shopping_category",
                weeks=0,
                metadata=selection.model_dump(mode="json"),
            )
        ]

    def default_next_collect_at(self, now: datetime | None = None) -> datetime:
        reference = now or datetime.now(timezone.utc)
        return reference + timedelta(minutes=1)
