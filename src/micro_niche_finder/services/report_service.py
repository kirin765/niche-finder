from micro_niche_finder.domain.schemas import FinalAnalysisInput, FinalAnalysisOutput
from micro_niche_finder.services.llm_service import OpenAIResearchService


class ReportService:
    def __init__(self, llm_service: OpenAIResearchService) -> None:
        self.llm_service = llm_service

    def build_report(self, analysis_input: FinalAnalysisInput) -> FinalAnalysisOutput:
        return self.llm_service.analyze_top_candidate(analysis_input)
