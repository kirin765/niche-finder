from pathlib import Path

from micro_niche_finder.domain.enums import FitLevel
from micro_niche_finder.domain.schemas import (
    FinalAnalysisInput,
    KeywordPageMapEntry,
    OnlineGTMContext,
    ScoreBreakdown,
    TrendFeatureSet,
)
from micro_niche_finder.services.brainstorming_v2_service import BrainstormingV2Service


class _SessionStub:
    def execute(self, *_args, **_kwargs):
        return self

    def fetchall(self):
        return []


class _ReportServiceStub:
    def build_report(self, payload):  # pragma: no cover - not used in these tests
        raise NotImplementedError(payload)


def _make_analysis_input() -> FinalAnalysisInput:
    return FinalAnalysisInput(
        canonical_name="동물병원 예약 관리",
        persona="동물병원 원장 겸 실무 관리자",
        buyer="동물병원 원장",
        problem_summary="예약 변경, 재진 안내, 미수금 추적이 카카오톡·전화·엑셀로 흩어져 있어 매일 수기로 확인해야 함",
        quantified_loss="하루 30분 이상 재확인 시간이 들고 누락이 발생한다.",
        current_spend="직원이 카톡과 엑셀로 직접 대응한다.",
        decision_maker_clarity=FitLevel.HIGH,
        manual_first_viability=FitLevel.HIGH,
        integration_lightness=FitLevel.MEDIUM,
        query_group=["동물병원 예약 관리", "동물병원 재진 안내"],
        features=TrendFeatureSet(
            recent_growth_4w=0.15,
            recent_growth_12w=0.2,
            moving_avg_ratio=1.0,
            volatility=0.15,
            spike_ratio=1.05,
            decay_after_peak=0.1,
            seasonality_score=0.1,
            query_diversity=0.5,
            problem_specificity=0.75,
            commercial_intent_ratio=0.55,
            brand_dependency_score=0.1,
            online_demand_score=0.62,
            absolute_demand_score=0.45,
            payability_score=0.6,
            market_size_sufficiency_score=0.55,
            online_gtm_efficiency_score=0.58,
            market_size_ceiling_score=0.42,
            competitive_whitespace_score=0.48,
            keyword_difficulty_score=0.4,
        ),
        score_breakdown=ScoreBreakdown(
            repeated_pain=0.82,
            problem_intensity=0.72,
            payment_likelihood=0.66,
            online_demand=0.61,
            market_size_sufficiency=0.55,
            online_gtm_efficiency=0.58,
            market_size_ceiling=0.42,
            competitive_whitespace=0.48,
            keyword_difficulty=0.6,
            implementation_feasibility=0.78,
            penalties=0.0,
            final_score=74.0,
            reasoning_summary="테스트",
        ),
        risk_flags=[],
        online_gtm_context=OnlineGTMContext(
            query="동물병원 예약 관리",
            summary="네이버 검색광고와 커뮤니티 유입 테스트가 가능하다.",
            channel_signals=["네이버 검색광고", "업종 커뮤니티"],
            channel_counts={"search_ads": 2, "community": 1},
            community_presence_score=0.5,
            seo_discoverability_score=0.5,
            competitor_presence_score=0.45,
            brand_concentration_score=0.2,
            competitive_whitespace_score=0.55,
            competitor_domains=["example.com"],
        ),
    )


def test_load_recent_reports_includes_llm_wiki_archive(tmp_path: Path) -> None:
    report_path = tmp_path / "auto-seeds-report-20260418-023328.md"
    report_path.write_text(
        "\n".join(
            [
                "# Auto Seeds Report",
                "",
                "## 동물병원 운영",
                "",
                "```json",
                "{",
                '  "niche_name": "동물병원 예약 관리",',
                '  "persona": "동물병원 원장 겸 실무 관리자",',
                '  "problem_summary": "예약 변경, 재진 안내, 미수금 추적이 카카오톡·전화·엑셀로 흩어져 있어 매일 수기로 확인해야 함"',
                "}",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    service = BrainstormingV2Service(report_service=_ReportServiceStub(), raw_report_dir=tmp_path)

    reports = service._load_recent_reports(_SessionStub())  # type: ignore[arg-type]

    assert reports == [
        {
            "seed_name": "동물병원 운영",
            "niche_name": "동물병원 예약 관리",
            "persona": "동물병원 원장 겸 실무 관리자",
            "problem_summary": "예약 변경, 재진 안내, 미수금 추적이 카카오톡·전화·엑셀로 흩어져 있어 매일 수기로 확인해야 함",
        }
    ]


def test_rank_candidates_uses_llm_wiki_archive_for_novelty(tmp_path: Path) -> None:
    report_path = tmp_path / "auto-seeds-report-20260418-023328.md"
    report_path.write_text(
        "\n".join(
            [
                "# Auto Seeds Report",
                "",
                "## 동물병원 운영",
                "",
                "```json",
                "{",
                '  "niche_name": "동물병원 예약 관리",',
                '  "persona": "동물병원 원장 겸 실무 관리자",',
                '  "problem_summary": "예약 변경, 재진 안내, 미수금 추적이 카카오톡·전화·엑셀로 흩어져 있어 매일 수기로 확인해야 함"',
                "}",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    service = BrainstormingV2Service(report_service=_ReportServiceStub(), raw_report_dir=tmp_path)

    ranked = service.rank_candidates(
        session=_SessionStub(),  # type: ignore[arg-type]
        scored_payloads=[(74.0, 1, 29, "동물병원 운영", _make_analysis_input())],
    )

    assert ranked[0].nearest_report_name == "동물병원 예약 관리"
    assert ranked[0].nearest_similarity >= 0.72
    assert ranked[0].novelty_score <= 0.25
