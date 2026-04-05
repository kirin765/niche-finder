from micro_niche_finder.domain.schemas import FinalAnalysisInput, FinalAnalysisOutput
from micro_niche_finder.services.report_service import ReportService


def run(payload: FinalAnalysisInput, report_service: ReportService) -> FinalAnalysisOutput:
    return report_service.build_report(payload)
