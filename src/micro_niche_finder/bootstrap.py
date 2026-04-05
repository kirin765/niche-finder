from dataclasses import dataclass
from functools import lru_cache

from micro_niche_finder.jobs.pipeline import PipelineService
from micro_niche_finder.services.clustering_service import QueryClusteringService
from micro_niche_finder.services.datalab_service import NaverDataLabService
from micro_niche_finder.services.feature_service import FeatureExtractionService
from micro_niche_finder.services.llm_service import OpenAIResearchService
from micro_niche_finder.services.report_service import ReportService
from micro_niche_finder.services.scoring_service import ScoringService


@dataclass(slots=True)
class ApplicationContainer:
    llm_service: OpenAIResearchService
    datalab_service: NaverDataLabService
    clustering_service: QueryClusteringService
    feature_service: FeatureExtractionService
    scoring_service: ScoringService
    report_service: ReportService
    pipeline_service: PipelineService


@lru_cache(maxsize=1)
def get_container() -> ApplicationContainer:
    llm_service = OpenAIResearchService()
    datalab_service = NaverDataLabService()
    clustering_service = QueryClusteringService()
    feature_service = FeatureExtractionService()
    scoring_service = ScoringService()
    report_service = ReportService(llm_service=llm_service)
    pipeline_service = PipelineService(
        llm_service=llm_service,
        datalab_service=datalab_service,
        clustering_service=clustering_service,
        feature_service=feature_service,
        scoring_service=scoring_service,
        report_service=report_service,
    )
    return ApplicationContainer(
        llm_service=llm_service,
        datalab_service=datalab_service,
        clustering_service=clustering_service,
        feature_service=feature_service,
        scoring_service=scoring_service,
        report_service=report_service,
        pipeline_service=pipeline_service,
    )
