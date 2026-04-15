from micro_niche_finder.domain.schemas import (
    FinalAnalysisInput,
    FinalAnalysisOutput,
    ScoreBreakdown,
    TrendFeatureSet,
)
from micro_niche_finder.services.report_service import ReportService


class StubLLMService:
    def analyze_top_candidate(self, payload: FinalAnalysisInput) -> FinalAnalysisOutput:
        return FinalAnalysisOutput(
            title="Micro Niche Daily Report",
            niche_name=payload.canonical_name,
            persona=payload.persona,
            buyer="",
            problem_summary=payload.problem_summary,
            core_value_proposition="",
            landing_page_hook="",
            saas_fit_score=74,
            trend_signal_score=63,
            payment_likelihood="medium",
            implementation_feasibility="high",
            mvp_idea=["접수", "상태 관리"],
            go_to_market=["검색", "커뮤니티"],
            first_10_leads=[],
            interview_questions=[],
            manual_first_offer=[],
            price_test=[],
            must_have_scope=[],
            must_not_build_scope=[],
            online_demand_summary="수요는 탐색 단계다.",
            market_size_summary="시장 근거는 제한적이다.",
            market_size_sufficiency_summary="solo founder 기준으로는 검토 가능하다.",
            search_evidence_summary="검색 근거는 초기 수준이다.",
            shopping_evidence_summary="해당 없음",
            public_data_summary="추가 확인 필요",
            online_gtm_summary="온라인 채널 접근 가능",
            recommended_online_channels=["네이버 검색"],
            validation_plan=[],
            kill_criteria=[],
            risk_flags=[],
            recommended_priority=1,
        )


def make_input() -> FinalAnalysisInput:
    return FinalAnalysisInput(
        canonical_name="학원 보강 일정 관리",
        persona="소형 학원 원장",
        buyer="학원 원장",
        problem_summary="보강 일정과 학부모 공지가 엉켜 누락이 발생한다.",
        quantified_loss="주당 여러 번 공지 누락과 상담 시간이 추가로 발생한다.",
        current_spend="원장과 상담실장이 카톡과 엑셀로 직접 대응한다.",
        decision_maker_clarity="high",
        manual_first_viability="high",
        integration_lightness="medium",
        query_group=["학원 보강 관리"],
        features=TrendFeatureSet(
            recent_growth_4w=0.1,
            recent_growth_12w=0.2,
            moving_avg_ratio=1.0,
            volatility=0.2,
            spike_ratio=1.1,
            decay_after_peak=0.1,
            seasonality_score=0.1,
            query_diversity=0.5,
            problem_specificity=0.7,
            commercial_intent_ratio=0.5,
            brand_dependency_score=0.1,
            online_demand_score=0.6,
            absolute_demand_score=0.4,
            payability_score=0.5,
            market_size_sufficiency_score=0.5,
            online_gtm_efficiency_score=0.5,
            market_size_ceiling_score=0.4,
            competitive_whitespace_score=0.4,
            keyword_difficulty_score=0.5,
        ),
        score_breakdown=ScoreBreakdown(
            repeated_pain=0.8,
            problem_intensity=0.7,
            payment_likelihood=0.6,
            online_demand=0.6,
            market_size_sufficiency=0.5,
            online_gtm_efficiency=0.5,
            market_size_ceiling=0.4,
            competitive_whitespace=0.4,
            keyword_difficulty=0.5,
            implementation_feasibility=0.8,
            penalties=0.0,
            final_score=72.0,
            reasoning_summary="테스트",
        ),
        risk_flags=[],
    )


def test_report_service_normalizes_generic_title_and_action_fields() -> None:
    service = ReportService(llm_service=StubLLMService())  # type: ignore[arg-type]

    report = service.build_report(make_input())

    assert report.title == "학원 보강 일정 관리 | 소형 학원 원장 운영 기회"
    assert report.buyer == "학원 원장"
    assert report.core_value_proposition
    assert report.landing_page_hook
    assert len(report.first_10_leads) == 3
    assert len(report.interview_questions) == 5
    assert len(report.manual_first_offer) == 3
    assert len(report.price_test) == 3
    assert len(report.must_have_scope) == 3
    assert len(report.must_not_build_scope) == 3
    assert len(report.validation_plan) == 3
    assert len(report.kill_criteria) == 3
