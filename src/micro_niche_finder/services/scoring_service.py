from __future__ import annotations

from dataclasses import dataclass

from micro_niche_finder.domain.enums import FitLevel, RepeatFrequency
from micro_niche_finder.domain.schemas import ProblemCandidateGenerated, ScoreBreakdown, TrendFeatureSet


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    repeated_pain: float = 0.28
    problem_intensity: float = 0.22
    payment_likelihood: float = 0.18
    persistent_signal: float = 0.12
    segment_focus: float = 0.08
    implementation_feasibility: float = 0.12


class ScoringService:
    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self.weights = weights or ScoreWeights()

    def score(self, candidate: ProblemCandidateGenerated, features: TrendFeatureSet) -> ScoreBreakdown:
        repeated_pain = self._repeat_score(candidate.repeat_frequency)
        problem_intensity = self._problem_intensity(candidate, features)
        payment = self._fit_score(candidate.payment_likelihood)
        persistent_signal = self._persistent_signal(features)
        segment_focus = self._segment_focus(features)
        implementation = self._implementation_fit(candidate, features)
        penalties = self._penalties(candidate, features)

        total = (
            repeated_pain * self.weights.repeated_pain
            + problem_intensity * self.weights.problem_intensity
            + payment * self.weights.payment_likelihood
            + persistent_signal * self.weights.persistent_signal
            + segment_focus * self.weights.segment_focus
            + implementation * self.weights.implementation_feasibility
            - penalties
        )
        final_score = round(max(0.0, min(100.0, total * 100)), 2)
        return ScoreBreakdown(
            repeated_pain=round(repeated_pain, 4),
            problem_intensity=round(problem_intensity, 4),
            payment_likelihood=round(payment, 4),
            persistent_signal=round(persistent_signal, 4),
            segment_focus=round(segment_focus, 4),
            implementation_feasibility=round(implementation, 4),
            penalties=round(penalties, 4),
            final_score=final_score,
            reasoning_summary=(
                f"repeat={repeated_pain:.2f}, problem={problem_intensity:.2f}, payment={payment:.2f}, "
                f"signal={persistent_signal:.2f}, segment={segment_focus:.2f}, implementation={implementation:.2f}, "
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

    def _problem_intensity(self, candidate: ProblemCandidateGenerated, features: TrendFeatureSet) -> float:
        pain_text = f"{candidate.job_to_be_done} {candidate.pain}".lower()
        intensity = 0.45
        for marker in ("누락", "실수", "시간", "매출", "cs", "손실"):
            if marker in pain_text:
                intensity += 0.08
        intensity += min(0.18, features.commercial_intent_ratio * 0.18)
        return min(intensity, 1.0)

    def _persistent_signal(self, features: TrendFeatureSet) -> float:
        growth = min(max((features.recent_growth_12w + 0.25), 0.0), 1.0)
        stability = 1.0 - min(features.volatility, 1.0)
        anti_spike = 1.0 - min(max(features.spike_ratio - 1.0, 0.0), 1.0)
        anti_decay = 1.0 - min(max(features.decay_after_peak, 0.0), 1.0)
        return max(0.0, min(1.0, (growth * 0.35) + (stability * 0.25) + (anti_spike * 0.2) + (anti_decay * 0.2)))

    def _segment_focus(self, features: TrendFeatureSet) -> float:
        return max(
            0.0,
            min(
                1.0,
                (features.age_concentration * 0.3)
                + (features.gender_concentration * 0.2)
                + (features.mobile_ratio * 0.15)
                + (features.segment_consistency * 0.35),
            ),
        )

    def _implementation_fit(self, candidate: ProblemCandidateGenerated, features: TrendFeatureSet) -> float:
        fit = self._fit_score(candidate.software_fit)
        fit += features.problem_specificity * 0.15
        fit -= features.brand_dependency_score * 0.15
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
        if "high_accuracy_required" in candidate.risk_flags:
            penalties += 0.08
        return penalties
