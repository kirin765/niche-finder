from micro_niche_finder.domain.schemas import ProblemCandidateGenerated, TrendFeatureSet
from micro_niche_finder.services.scoring_service import ScoringService


def make_features(**overrides) -> TrendFeatureSet:
    base = {
        "recent_growth_4w": 0.18,
        "recent_growth_12w": 0.25,
        "moving_avg_ratio": 1.08,
        "volatility": 0.18,
        "spike_ratio": 1.2,
        "decay_after_peak": 0.1,
        "seasonality_score": 0.22,
        "age_concentration": 0.64,
        "gender_concentration": 0.56,
        "mobile_ratio": 0.7,
        "segment_consistency": 0.72,
        "query_diversity": 0.75,
        "problem_specificity": 0.8,
        "commercial_intent_ratio": 0.68,
        "brand_dependency_score": 0.15,
    }
    base.update(overrides)
    return TrendFeatureSet(**base)


def make_candidate(**overrides) -> ProblemCandidateGenerated:
    base = {
        "seed_category": "스마트스토어 운영",
        "persona": "소형 셀러",
        "job_to_be_done": "경쟁 상품 가격을 매일 확인한다",
        "pain": "수작업으로 누락과 시간 낭비가 잦다",
        "repeat_frequency": "daily",
        "current_workaround": ["엑셀", "수동 검색"],
        "software_fit": "high",
        "payment_likelihood": "medium",
        "risk_flags": [],
        "query_candidates": ["경쟁사 가격 확인", "가격 모니터링"],
    }
    base.update(overrides)
    return ProblemCandidateGenerated(**base)


def test_repeated_operational_pain_scores_well() -> None:
    service = ScoringService()
    score = service.score(make_candidate(), make_features())
    assert score.final_score > 70
    assert score.penalties < 0.1


def test_news_spike_and_platform_dependency_are_penalized() -> None:
    service = ScoringService()
    candidate = make_candidate(risk_flags=["depends_on_external_platform"])
    features = make_features(spike_ratio=2.3, seasonality_score=0.75)
    score = service.score(candidate, features)
    assert score.penalties >= 0.18
    assert score.final_score < 75


def test_one_off_low_fit_candidate_stays_low() -> None:
    service = ScoringService()
    candidate = make_candidate(
        repeat_frequency="one_off",
        software_fit="low",
        payment_likelihood="low",
        pain="일회성 정보 탐색 수요다",
    )
    features = make_features(recent_growth_12w=-0.2, volatility=0.6, commercial_intent_ratio=0.2)
    score = service.score(candidate, features)
    assert score.repeated_pain < 0.2
    assert score.final_score < 45
