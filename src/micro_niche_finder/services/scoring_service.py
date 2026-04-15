from __future__ import annotations

from dataclasses import dataclass

from micro_niche_finder.domain.enums import FitLevel, RepeatFrequency
from micro_niche_finder.domain.schemas import ProblemCandidateGenerated, ScoreBreakdown, TrendFeatureSet
from micro_niche_finder.services.public_data_opportunity_service import PublicDataOpportunityService


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    repeated_pain: float = 0.15
    problem_intensity: float = 0.12
    payment_likelihood: float = 0.11
    online_demand: float = 0.18
    market_size_sufficiency: float = 0.09
    online_gtm_efficiency: float = 0.15
    market_size_ceiling: float = 0.10
    competitive_whitespace: float = 0.05
    keyword_difficulty: float = 0.10
    implementation_feasibility: float = 0.04


class ScoringService:
    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self.weights = weights or ScoreWeights()
        self.public_data_opportunity_service = PublicDataOpportunityService()

    def score(self, candidate: ProblemCandidateGenerated, features: TrendFeatureSet) -> ScoreBreakdown:
        repeated_pain = self._repeat_score(candidate.repeat_frequency)
        problem_intensity = self._problem_intensity(candidate, features)
        payment = self._payment_score(candidate, features)
        online_demand = self._online_demand_score(candidate, features)
        market_size_sufficiency = self._market_size_sufficiency_score(candidate, features)
        online_gtm_efficiency = self._online_gtm_efficiency_score(candidate, features)
        market_size_ceiling = self._market_size_ceiling_score(features)
        competitive_whitespace = self._competitive_whitespace_score(features)
        keyword_difficulty = self._keyword_difficulty_score(features)
        implementation = self._implementation_fit(candidate, features)
        penalties = self._penalties(candidate, features)

        total = (
            repeated_pain * self.weights.repeated_pain
            + problem_intensity * self.weights.problem_intensity
            + payment * self.weights.payment_likelihood
            + online_demand * self.weights.online_demand
            + market_size_sufficiency * self.weights.market_size_sufficiency
            + online_gtm_efficiency * self.weights.online_gtm_efficiency
            + market_size_ceiling * self.weights.market_size_ceiling
            + competitive_whitespace * self.weights.competitive_whitespace
            + keyword_difficulty * self.weights.keyword_difficulty
            + implementation * self.weights.implementation_feasibility
            - penalties
        )
        final_score = round(max(0.0, min(100.0, total * 100)), 2)
        return ScoreBreakdown(
            repeated_pain=round(repeated_pain, 4),
            problem_intensity=round(problem_intensity, 4),
            payment_likelihood=round(payment, 4),
            online_demand=round(online_demand, 4),
            market_size_sufficiency=round(market_size_sufficiency, 4),
            online_gtm_efficiency=round(online_gtm_efficiency, 4),
            market_size_ceiling=round(market_size_ceiling, 4),
            competitive_whitespace=round(competitive_whitespace, 4),
            keyword_difficulty=round(keyword_difficulty, 4),
            implementation_feasibility=round(implementation, 4),
            penalties=round(penalties, 4),
            final_score=final_score,
            reasoning_summary=(
                f"repeat={repeated_pain:.2f}, problem={problem_intensity:.2f}, payment={payment:.2f}, "
                f"online_demand={online_demand:.2f}, market={market_size_sufficiency:.2f}, "
                f"online_gtm={online_gtm_efficiency:.2f}, ceiling={market_size_ceiling:.2f}, "
                f"whitespace={competitive_whitespace:.2f}, keyword={keyword_difficulty:.2f}, "
                f"implementation={implementation:.2f}, "
                f"penalties={penalties:.2f}"
            ),
        )

    def _repeat_score(self, frequency: RepeatFrequency) -> float:
        mapping = {
            RepeatFrequency.DAILY: 1.0,
            RepeatFrequency.WEEKLY: 0.82,
            RepeatFrequency.MONTHLY: 0.58,
            RepeatFrequency.OCCASIONAL: 0.35,
            RepeatFrequency.ONE_OFF: 0.12,
        }
        return mapping[frequency]

    def _fit_score(self, level: FitLevel) -> float:
        return {
            FitLevel.HIGH: 0.9,
            FitLevel.MEDIUM: 0.62,
            FitLevel.LOW: 0.28,
        }[level]

    def _payment_score(self, candidate: ProblemCandidateGenerated, features: TrendFeatureSet) -> float:
        prior = self._fit_score(candidate.payment_likelihood)
        evidence = max(0.0, min(1.0, features.payability_score))
        decision_maker = self._fit_score(candidate.decision_maker_clarity)
        current_spend = self._current_spend_signal(candidate)
        return max(0.0, min(1.0, (prior * 0.45) + (evidence * 0.3) + (decision_maker * 0.15) + (current_spend * 0.1)))

    def _problem_intensity(self, candidate: ProblemCandidateGenerated, features: TrendFeatureSet) -> float:
        pain_text = f"{candidate.job_to_be_done} {candidate.pain}".lower()
        intensity = 0.45
        for marker in ("누락", "실수", "시간", "매출", "cs", "손실"):
            if marker in pain_text:
                intensity += 0.08
        intensity += self._manual_workaround_signal(candidate) * 0.08
        intensity += self._quantified_loss_signal(candidate) * 0.12
        intensity += min(0.18, features.commercial_intent_ratio * 0.18)
        return min(intensity, 1.0)

    def _online_demand_score(self, candidate: ProblemCandidateGenerated, features: TrendFeatureSet) -> float:
        score = features.online_demand_score * 0.45
        score += features.absolute_demand_score * 0.3
        score += self._fit_score(candidate.market_size_confidence) * 0.04
        score += min(1.0, len(candidate.query_candidates) / 4) * 0.05
        score += self._fit_score(candidate.online_gtm_fit) * 0.06
        score += features.commercial_intent_ratio * 0.1
        score += self._trackable_acquisition_signal(candidate) * 0.05
        return max(0.0, min(1.0, score))

    def _market_size_sufficiency_score(self, candidate: ProblemCandidateGenerated, features: TrendFeatureSet) -> float:
        score = features.market_size_sufficiency_score * 0.8
        score += self._fit_score(candidate.market_size_confidence) * 0.15
        score += self._public_data_leverage(candidate) * 0.05
        return max(0.0, min(1.0, score))

    def _online_gtm_efficiency_score(self, candidate: ProblemCandidateGenerated, features: TrendFeatureSet) -> float:
        channels = min(1.0, len(candidate.online_acquisition_channels) / 3)
        trackable = self._trackable_acquisition_signal(candidate)
        score = features.online_gtm_efficiency_score * 0.45
        score += self._fit_score(candidate.online_gtm_fit) * 0.15
        score += channels * 0.05
        score += trackable * 0.15
        score += features.absolute_demand_score * 0.1
        score += (1.0 - features.keyword_difficulty_score) * 0.1
        return max(0.0, min(1.0, score))

    def _market_size_ceiling_score(self, features: TrendFeatureSet) -> float:
        return max(0.0, min(1.0, features.market_size_ceiling_score))

    def _competitive_whitespace_score(self, features: TrendFeatureSet) -> float:
        return max(0.0, min(1.0, features.competitive_whitespace_score))

    def _keyword_difficulty_score(self, features: TrendFeatureSet) -> float:
        return max(0.0, min(1.0, 1.0 - features.keyword_difficulty_score))

    def _implementation_fit(self, candidate: ProblemCandidateGenerated, features: TrendFeatureSet) -> float:
        fit = self._fit_score(candidate.software_fit)
        fit += features.problem_specificity * 0.15
        fit += self._solo_builder_bonus(candidate) * 0.18
        fit += self._public_data_leverage(candidate) * 0.08
        fit += self._fit_score(candidate.manual_first_viability) * 0.12
        fit += self._fit_score(candidate.integration_lightness) * 0.12
        fit -= features.brand_dependency_score * 0.15
        fit -= self._broad_scope_signal(candidate) * 0.18
        if "regulation_risk" in candidate.risk_flags:
            fit -= 0.25
        if "enterprise_complexity" in candidate.risk_flags:
            fit -= 0.2
        return max(0.0, min(1.0, fit))

    def _penalties(self, candidate: ProblemCandidateGenerated, features: TrendFeatureSet) -> float:
        penalties = 0.0
        if features.spike_ratio > 1.8:
            penalties += 0.08
        if features.seasonality_score > 0.65:
            penalties += 0.05
        if features.brand_dependency_score > 0.55:
            penalties += 0.07
        if "depends_on_external_platform" in candidate.risk_flags:
            penalties += 0.05
        if "regulation_risk" in candidate.risk_flags:
            penalties += 0.12
        if "enterprise_complexity" in candidate.risk_flags:
            penalties += 0.08
        if "high_accuracy_required" in candidate.risk_flags:
            penalties += 0.08
        if "regulation_risk" in candidate.risk_flags and self._public_data_regulatory_signal(candidate) > 0:
            penalties += 0.04
        if features.online_demand_score < 0.3:
            penalties += 0.1
        if features.absolute_demand_score < 0.25:
            penalties += 0.12
        elif features.absolute_demand_score < 0.4:
            penalties += 0.06
        if features.online_gtm_efficiency_score < 0.25:
            penalties += 0.08
        if self._trackable_acquisition_signal(candidate) < 0.35:
            penalties += 0.08
        if features.market_size_ceiling_score < 0.3:
            penalties += 0.1
        if features.competitive_whitespace_score < 0.25:
            penalties += 0.06
        if features.keyword_difficulty_score > 0.75:
            penalties += 0.08
        penalties += self._broad_scope_signal(candidate) * 0.06
        return penalties

    def _manual_workaround_signal(self, candidate: ProblemCandidateGenerated) -> float:
        markers = ("엑셀", "수기", "카톡", "카카오톡", "문자", "전화", "메모", "이메일", "톡톡", "복붙")
        text = " ".join(candidate.current_workaround + [candidate.job_to_be_done, candidate.pain]).lower()
        hits = sum(1 for marker in markers if marker in text)
        return min(1.0, hits / 3)

    def _quantified_loss_signal(self, candidate: ProblemCandidateGenerated) -> float:
        text = f"{candidate.quantified_loss} {candidate.pain}".lower()
        markers = ("시간", "분", "시간씩", "매출", "손실", "누락", "노쇼", "이탈", "미수금", "건", "주당", "매일", "월")
        hits = sum(1 for marker in markers if marker in text)
        has_digit = any(char.isdigit() for char in text)
        base = min(1.0, hits / 4)
        if has_digit:
            base = min(1.0, base + 0.2)
        return base

    def _current_spend_signal(self, candidate: ProblemCandidateGenerated) -> float:
        text = f"{candidate.current_spend} {' '.join(candidate.current_workaround)}".lower()
        markers = ("엑셀", "알바", "직원", "시간", "외주", "수기", "카톡", "문자", "전화", "월", "비용", "대행")
        hits = sum(1 for marker in markers if marker in text)
        return min(1.0, hits / 4)

    def _trackable_acquisition_signal(self, candidate: ProblemCandidateGenerated) -> float:
        text = " ".join(candidate.online_acquisition_channels).lower()
        markers = ("검색", "광고", "seo", "블로그", "콘텐츠", "유튜브", "카페", "커뮤니티", "랜딩")
        hits = sum(1 for marker in markers if marker in text)
        return min(1.0, hits / 4)

    def _solo_builder_bonus(self, candidate: ProblemCandidateGenerated) -> float:
        text = " ".join(
            [
                candidate.persona,
                candidate.job_to_be_done,
                candidate.pain,
                *candidate.current_workaround,
                *candidate.query_candidates,
            ]
        ).lower()
        narrow_markers = (
            "예약",
            "정산",
            "수납",
            "입금",
            "문의",
            "배정",
            "스케줄",
            "출결",
            "재고",
            "발주",
            "리마인드",
            "노쇼",
            "청구",
            "미수금",
            "환불",
            "보강",
        )
        operator_markers = ("원장", "사장", "운영자", "실장", "매니저", "셀러", "1인", "소형", "작은")
        manual_bonus = self._manual_workaround_signal(candidate) * 0.45
        narrow_bonus = min(1.0, sum(1 for marker in narrow_markers if marker in text) / 4) * 0.35
        operator_bonus = min(1.0, sum(1 for marker in operator_markers if marker in text) / 2) * 0.2
        return min(1.0, manual_bonus + narrow_bonus + operator_bonus)

    def _broad_scope_signal(self, candidate: ProblemCandidateGenerated) -> float:
        text = " ".join(
            [
                candidate.persona,
                candidate.job_to_be_done,
                candidate.pain,
                *candidate.current_workaround,
                *candidate.query_candidates,
            ]
        ).lower()
        broad_markers = (
            "올인원",
            "전사",
            "그룹웨어",
            "erp",
            "crm",
            "마케팅",
            "브랜딩",
            "콘텐츠",
            "광고",
            "통합 플랫폼",
            "대기업",
            "엔터프라이즈",
        )
        hits = sum(1 for marker in broad_markers if marker in text)
        return min(1.0, hits / 3)

    def _public_data_leverage(self, candidate: ProblemCandidateGenerated) -> float:
        return self.public_data_opportunity_service.leverage_score(
            canonical_name=" ".join(candidate.query_candidates[:1]) or candidate.job_to_be_done,
            persona=candidate.persona,
            problem_summary=candidate.pain,
            query_group=candidate.query_candidates,
        )

    def _public_data_regulatory_signal(self, candidate: ProblemCandidateGenerated) -> float:
        text = " ".join(
            [
                candidate.persona,
                candidate.job_to_be_done,
                candidate.pain,
                *candidate.current_workaround,
                *candidate.query_candidates,
            ]
        ).lower()
        markers = ("의료기기", "품목허가", "푸드", "원재료", "알레르기", "영양표시", "식품표시")
        hits = sum(1 for marker in markers if marker in text)
        return min(1.0, hits / 2)
