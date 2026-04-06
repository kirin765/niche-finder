from __future__ import annotations

from statistics import mean, pstdev

from micro_niche_finder.domain.schemas import DataLabResponse, TrendFeatureSet


class FeatureExtractionService:
    PROBLEM_MARKERS = ("관리", "누락", "정산", "수납", "예약", "문의", "출결", "보강", "노쇼", "미수금", "재고", "발주")
    COMMERCIAL_MARKERS = ("프로그램", "솔루션", "자동화", "툴", "서비스", "비교", "추천", "crm", "erp")
    BRAND_MARKERS = ("네이버", "naver", "카카오", "kakao", "쿠팡", "coupang", "배민", "smartstore", "스마트스토어")

    def extract(self, response: DataLabResponse, query_count: int, queries: list[str]) -> TrendFeatureSet:
        series = response.results[0].data
        values = [point.ratio for point in series]
        query_diversity = round(min(1.0, query_count / 6), 4)
        problem_specificity = self._problem_specificity(queries)
        commercial_intent_ratio = self._commercial_intent_ratio(queries)
        brand_dependency_score = self._brand_dependency_score(queries)
        if not values:
            return TrendFeatureSet(
                recent_growth_4w=0.0,
                recent_growth_12w=0.0,
                moving_avg_ratio=0.0,
                volatility=1.0,
                spike_ratio=0.0,
                decay_after_peak=0.0,
                seasonality_score=0.0,
                query_diversity=query_diversity,
                problem_specificity=problem_specificity,
                commercial_intent_ratio=commercial_intent_ratio,
                brand_dependency_score=brand_dependency_score,
                online_demand_score=round(
                    max(0.1, min(0.7, (problem_specificity * 0.5) + (commercial_intent_ratio * 0.3) + (query_diversity * 0.2))),
                    4,
                ),
                absolute_demand_score=0.4,
                payability_score=0.5,
                market_size_sufficiency_score=0.5,
                online_gtm_efficiency_score=round(
                    max(
                        0.15,
                        min(
                            0.7,
                            (commercial_intent_ratio * 0.45)
                            + (problem_specificity * 0.3)
                            + ((1.0 - brand_dependency_score) * 0.15)
                            + (query_diversity * 0.1),
                        ),
                    ),
                    4,
                ),
                market_size_ceiling_score=0.7,
                competitive_whitespace_score=0.6,
                keyword_difficulty_score=0.5,
            )
        recent_4 = values[-4:] if len(values) >= 4 else values
        recent_12 = values[-12:] if len(values) >= 12 else values
        baseline = mean(values[:-4] or values)
        latest_avg = mean(recent_4 or values)
        full_avg = mean(values)
        peak = max(values)
        trough = min(values)
        volatility = pstdev(values) / max(full_avg, 1.0)
        spike_ratio = peak / max(full_avg, 1.0)
        decay = (peak - values[-1]) / max(peak, 1.0)
        seasonality = max(0.0, min(1.0, (peak - trough) / max(peak, 1.0)))

        persistent_signal = min(max((mean(recent_12 or values) - values[0]) / max(values[0], 1.0) + 0.25, 0.0), 1.0)
        online_demand = max(
            0.0,
            min(1.0, (persistent_signal * 0.45) + (problem_specificity * 0.3) + (commercial_intent_ratio * 0.25)),
        )
        market_size_sufficiency = max(
            0.0,
            min(1.0, 0.4 + query_diversity * 0.25 + commercial_intent_ratio * 0.2 + problem_specificity * 0.15),
        )
        online_gtm_efficiency = max(
            0.0,
            min(
                1.0,
                (
                    commercial_intent_ratio * 0.4
                    + problem_specificity * 0.25
                    + (1.0 - brand_dependency_score) * 0.2
                    + query_diversity * 0.15
                ),
            ),
        )

        return TrendFeatureSet(
            recent_growth_4w=round((latest_avg - baseline) / max(baseline, 1.0), 4),
            recent_growth_12w=round((mean(recent_12 or values) - values[0]) / max(values[0], 1.0), 4),
            moving_avg_ratio=round(latest_avg / max(full_avg, 1.0), 4),
            volatility=round(volatility, 4),
            spike_ratio=round(spike_ratio, 4),
            decay_after_peak=round(decay, 4),
            seasonality_score=round(seasonality, 4),
            query_diversity=query_diversity,
            problem_specificity=problem_specificity,
            commercial_intent_ratio=commercial_intent_ratio,
            brand_dependency_score=brand_dependency_score,
            online_demand_score=round(online_demand, 4),
            absolute_demand_score=round(min(0.85, 0.3 + query_diversity * 0.3 + commercial_intent_ratio * 0.2), 4),
            payability_score=round(min(0.8, 0.35 + commercial_intent_ratio * 0.25 + problem_specificity * 0.2), 4),
            market_size_sufficiency_score=round(market_size_sufficiency, 4),
            online_gtm_efficiency_score=round(online_gtm_efficiency, 4),
            market_size_ceiling_score=0.7,
            competitive_whitespace_score=0.6,
            keyword_difficulty_score=round(
                max(
                    0.2,
                    min(
                        0.8,
                        (brand_dependency_score * 0.45)
                        + ((1.0 - problem_specificity) * 0.2)
                        + ((1.0 - query_diversity) * 0.2)
                        + ((1.0 - commercial_intent_ratio) * 0.15),
                    ),
                ),
                4,
            ),
        )

    def _problem_specificity(self, queries: list[str]) -> float:
        if not queries:
            return 0.4
        text = " ".join(queries).lower()
        marker_hits = sum(1 for marker in self.PROBLEM_MARKERS if marker in text)
        avg_terms = sum(len(query.split()) for query in queries) / max(len(queries), 1)
        return round(min(1.0, 0.3 + min(0.4, marker_hits * 0.08) + min(0.3, avg_terms / 10)), 4)

    def _commercial_intent_ratio(self, queries: list[str]) -> float:
        if not queries:
            return 0.2
        text = " ".join(queries).lower()
        hits = sum(1 for marker in self.COMMERCIAL_MARKERS if marker in text)
        return round(min(1.0, 0.15 + hits * 0.12), 4)

    def _brand_dependency_score(self, queries: list[str]) -> float:
        if not queries:
            return 0.0
        text = " ".join(queries).lower()
        hits = sum(1 for marker in self.BRAND_MARKERS if marker in text)
        return round(min(1.0, hits * 0.18), 4)
