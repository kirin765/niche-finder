from __future__ import annotations

from statistics import mean, pstdev

from micro_niche_finder.domain.schemas import DataLabResponse, TrendFeatureSet


class FeatureExtractionService:
    def extract(self, response: DataLabResponse, query_count: int) -> TrendFeatureSet:
        series = response.results[0].data
        values = [point.ratio for point in series]
        if not values:
            return TrendFeatureSet(
                recent_growth_4w=0.0,
                recent_growth_12w=0.0,
                moving_avg_ratio=0.0,
                volatility=1.0,
                spike_ratio=0.0,
                decay_after_peak=0.0,
                seasonality_score=0.0,
                age_concentration=0.0,
                gender_concentration=0.0,
                mobile_ratio=0.0,
                segment_consistency=0.0,
                query_diversity=round(min(1.0, query_count / 6), 4),
                problem_specificity=0.4,
                commercial_intent_ratio=0.2,
                brand_dependency_score=0.0,
                online_demand_score=0.25,
                market_size_sufficiency_score=0.5,
                online_gtm_efficiency_score=0.25,
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

        online_demand = max(
            0.0,
            min(
                1.0,
                (
                    min(max((mean(recent_12 or values) - values[0]) / max(values[0], 1.0) + 0.25, 0.0), 1.0) * 0.45
                    + 0.74 * 0.3
                    + 0.63 * 0.25
                ),
            ),
        )
        market_size_sufficiency = max(0.0, min(1.0, 0.4 + min(1.0, query_count / 6) * 0.25 + 0.63 * 0.2 + 0.74 * 0.15))
        online_gtm_efficiency = max(
            0.0,
            min(
                1.0,
                (
                    0.63 * 0.4
                    + 0.74 * 0.25
                    + (1.0 - 0.18) * 0.2
                    + min(1.0, query_count / 6) * 0.15
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
            age_concentration=0.62,
            gender_concentration=0.54,
            mobile_ratio=0.71,
            segment_consistency=0.66,
            query_diversity=round(min(1.0, query_count / 6), 4),
            problem_specificity=0.74,
            commercial_intent_ratio=0.63,
            brand_dependency_score=0.18,
            online_demand_score=round(online_demand, 4),
            market_size_sufficiency_score=round(market_size_sufficiency, 4),
            online_gtm_efficiency_score=round(online_gtm_efficiency, 4),
        )
