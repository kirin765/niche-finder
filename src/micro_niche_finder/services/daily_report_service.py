from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import FinalAnalysisOutput
from micro_niche_finder.repos.candidate_repo import SeedCategoryRepository
from micro_niche_finder.services.gmail_service import GmailService
from micro_niche_finder.services.telegram_service import TelegramService


@dataclass(slots=True)
class DailySeedReport:
    seed_id: int
    seed_name: str
    report: FinalAnalysisOutput


@dataclass(slots=True)
class DailyReportRunSummary:
    timezone: str
    generated_at: str
    seeds_processed: int
    messages_sent: int
    emails_sent: int
    niches: list[str]


class DailyReportService:
    def __init__(
        self,
        *,
        pipeline_service,
        telegram_service: TelegramService,
        gmail_service: GmailService,
    ) -> None:
        self.settings = get_settings()
        self.pipeline_service = pipeline_service
        self.telegram_service = telegram_service
        self.gmail_service = gmail_service

    def run(self, *, session: Session) -> DailyReportRunSummary:
        if not self.telegram_service.is_configured() and not self.gmail_service.is_configured():
            raise RuntimeError("No daily report delivery channel is configured")

        repo = SeedCategoryRepository(session)
        seeds = repo.list_all()[: self.settings.daily_report_seed_limit]
        if not seeds:
            raise RuntimeError("No seed categories exist for daily report generation")

        generated_at = datetime.now(ZoneInfo(self.settings.daily_report_timezone))
        seed_reports: list[DailySeedReport] = []
        for seed in seeds:
            pipeline = self.pipeline_service.run(
                session=session,
                seed_category_id=seed.id,
                candidate_count=self.settings.daily_report_candidate_count,
                top_k=self.settings.daily_report_top_k_per_seed,
            )
            session.commit()
            if not pipeline.reports:
                continue
            seed_reports.append(
                DailySeedReport(
                    seed_id=seed.id,
                    seed_name=seed.name,
                    report=pipeline.reports[0],
                )
            )

        if not seed_reports:
            raise RuntimeError("Daily report generation produced no reports")

        message = self._format_message(seed_reports, generated_at)
        messages_sent = self.telegram_service.send_message(message) if self.telegram_service.is_configured() else 0
        emails_sent = (
            self.gmail_service.send_email(
                subject=self._email_subject(generated_at),
                body=message,
            )
            if self.gmail_service.is_configured()
            else 0
        )
        return DailyReportRunSummary(
            timezone=self.settings.daily_report_timezone,
            generated_at=generated_at.isoformat(),
            seeds_processed=len(seed_reports),
            messages_sent=messages_sent,
            emails_sent=emails_sent,
            niches=[item.report.niche_name for item in seed_reports],
        )

    def _format_message(self, seed_reports: list[DailySeedReport], generated_at: datetime) -> str:
        header = (
            f"[Micro Niche Daily Report]\n"
            f"- Time: {generated_at.strftime('%Y-%m-%d %H:%M %Z')}\n"
            f"- Seeds processed: {len(seed_reports)}"
        )
        sections = [self._format_seed_report(item) for item in seed_reports]
        return "\n\n".join([header, *sections])

    @staticmethod
    def _email_subject(generated_at: datetime) -> str:
        return f"[Micro Niche Daily Report] {generated_at.strftime('%Y-%m-%d %H:%M %Z')}"

    @staticmethod
    def _format_seed_report(item: DailySeedReport) -> str:
        report = item.report
        mvp = "; ".join(report.mvp_idea[:3])
        risks = ", ".join(report.risk_flags[:3]) if report.risk_flags else "없음"
        return (
            f"[{item.seed_name}] {report.niche_name}\n"
            f"문제: {report.problem_summary}\n"
            f"구현성: {report.implementation_feasibility}\n"
            f"MVP: {mvp}\n"
            f"검색근거: {report.search_evidence_summary}\n"
            f"시장근거: {report.market_size_summary}\n"
            f"공공데이터: {report.public_data_summary}\n"
            f"리스크: {risks}"
        )
