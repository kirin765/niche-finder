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


def test_manual_narrow_operator_workflow_gets_solo_builder_boost() -> None:
    service = ScoringService()
    candidate = make_candidate(
        persona="1인 피부관리실 원장",
        job_to_be_done="예약 변경과 재예약 누락을 매일 확인한다",
        pain="엑셀과 카톡으로 관리해 누락과 공실 손실이 반복된다",
        current_workaround=["엑셀", "카카오톡", "수기 메모"],
        query_candidates=["피부관리실 예약 관리", "노쇼 방지 프로그램"],
    )
    score = service.score(candidate, make_features())

    assert score.implementation_feasibility > 0.9
    assert score.final_score > 75


def test_broad_enterprise_scope_is_penalized_for_solo_founder() -> None:
    service = ScoringService()
    candidate = make_candidate(
        persona="중견기업 운영팀",
        job_to_be_done="전사 ERP와 CRM을 통합한 올인원 운영 플랫폼을 도입한다",
        pain="여러 부서가 사용하는 그룹웨어와 마케팅 플랫폼을 한 번에 통합하고 싶다",
        current_workaround=["ERP", "CRM", "그룹웨어"],
        query_candidates=["ERP 통합 플랫폼", "올인원 CRM", "전사 운영 플랫폼"],
        risk_flags=["enterprise_complexity"],
    )
    score = service.score(candidate, make_features())

    assert score.penalties >= 0.1
    assert score.implementation_feasibility < 0.75
    assert score.final_score < 70


def test_public_data_leverage_boosts_fragmented_commerce_workflows() -> None:
    service = ScoringService()
    candidate = make_candidate(
        persona="소형 스마트스토어 셀러",
        job_to_be_done="통신판매 상품 정산과 가격 점검을 매일 확인한다",
        pain="셀러 운영과 사업자 확인을 엑셀로 관리해 누락이 잦다",
        current_workaround=["엑셀", "사업자번호 수기 확인"],
        query_candidates=["스마트스토어 정산 관리", "통신판매 사업자 확인"],
    )
    score = service.score(candidate, make_features())

    assert score.implementation_feasibility > 0.9
    assert score.final_score > 75
