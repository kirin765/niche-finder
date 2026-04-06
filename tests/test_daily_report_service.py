from dataclasses import dataclass
from types import SimpleNamespace

from micro_niche_finder.domain.schemas import FinalAnalysisOutput
from micro_niche_finder.services import daily_report_service as daily_report_module
from micro_niche_finder.services.daily_report_service import DailyReportService, DailySeedReport


@dataclass
class _FakePipelineService:
    pass


@dataclass
class _FakeTelegramService:
    def is_configured(self) -> bool:
        return True

    def send_message(self, text: str) -> int:
        return 1


@dataclass
class _FakeGmailService:
    def is_configured(self) -> bool:
        return True

    def send_email(self, *, subject: str, body: str) -> int:
        return 2


@dataclass
class _FakeSession:
    def commit(self) -> None:
        return None


def test_daily_report_service_formats_seed_sections() -> None:
    service = DailyReportService(
        pipeline_service=_FakePipelineService(),
        telegram_service=_FakeTelegramService(),
        gmail_service=_FakeGmailService(),
    )
    report = FinalAnalysisOutput(
        niche_name="학원 상담 누락 방지",
        persona="학원 원장",
        problem_summary="상담 누락이 반복된다.",
        saas_fit_score=80,
        trend_signal_score=60,
        payment_likelihood="높음",
        implementation_feasibility="높음",
        mvp_idea=["상담 입력", "후속 리마인드", "누락 알림"],
        go_to_market=["SEO"],
        online_demand_summary="온라인 검색 수요가 있다",
        market_size_summary="시장 근거",
        market_size_sufficiency_summary="시장 규모는 충분하다",
        search_evidence_summary="검색 근거",
        shopping_evidence_summary="쇼핑 근거 없음",
        public_data_summary="공공데이터 근거",
        online_gtm_summary="검색과 커뮤니티로 접근 가능하다",
        recommended_online_channels=["네이버 검색", "원장 커뮤니티"],
        risk_flags=["카카오톡 의존"],
        recommended_priority=1,
    )

    section = service._format_seed_report(DailySeedReport(seed_id=1, seed_name="학원 운영", report=report))

    assert "[학원 운영] 학원 상담 누락 방지" in section
    assert "검색근거: 검색 근거" in section
    assert "공공데이터: 공공데이터 근거" in section


def test_daily_report_service_run_sends_all_configured_channels(monkeypatch) -> None:
    report = FinalAnalysisOutput(
        niche_name="학원 상담 누락 방지",
        persona="학원 원장",
        problem_summary="상담 누락이 반복된다.",
        saas_fit_score=80,
        trend_signal_score=60,
        payment_likelihood="높음",
        implementation_feasibility="높음",
        mvp_idea=["상담 입력", "후속 리마인드", "누락 알림"],
        go_to_market=["SEO"],
        online_demand_summary="온라인 검색 수요가 있다",
        market_size_summary="시장 근거",
        market_size_sufficiency_summary="시장 규모는 충분하다",
        search_evidence_summary="검색 근거",
        shopping_evidence_summary="쇼핑 근거 없음",
        public_data_summary="공공데이터 근거",
        online_gtm_summary="검색과 커뮤니티로 접근 가능하다",
        recommended_online_channels=["네이버 검색", "원장 커뮤니티"],
        risk_flags=["카카오톡 의존"],
        recommended_priority=1,
    )

    class _Repo:
        def list_all(self):
            return [SimpleNamespace(id=1, name="학원 운영")]

    class _Pipeline:
        def run(self, **kwargs):
            return SimpleNamespace(reports=[report])

    monkeypatch.setattr(daily_report_module, "SeedCategoryRepository", lambda session: _Repo())
    service = DailyReportService(
        pipeline_service=_Pipeline(),
        telegram_service=_FakeTelegramService(),
        gmail_service=_FakeGmailService(),
    )

    summary = service.run(session=_FakeSession())

    assert summary.seeds_processed == 1
    assert summary.messages_sent == 1
    assert summary.emails_sent == 2
    assert summary.niches == ["학원 상담 누락 방지"]
