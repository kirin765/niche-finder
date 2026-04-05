from dataclasses import dataclass
from functools import lru_cache

from micro_niche_finder.jobs.pipeline import PipelineService
from micro_niche_finder.services.budget_allocator_service import BudgetAllocatorService
from micro_niche_finder.services.collection_scheduler_service import CollectionSchedulerService
from micro_niche_finder.services.collector_service import CollectorService
from micro_niche_finder.services.clustering_service import QueryClusteringService
from micro_niche_finder.services.datalab_service import NaverDataLabService
from micro_niche_finder.services.feature_service import FeatureExtractionService
from micro_niche_finder.services.google_collector_service import GoogleCollectorService
from micro_niche_finder.services.google_search_service import GoogleSearchService
from micro_niche_finder.services.llm_service import OpenAIResearchService
from micro_niche_finder.services.report_service import ReportService
from micro_niche_finder.services.scoring_service import ScoringService


@dataclass(slots=True)
class ApplicationContainer:
    llm_service: OpenAIResearchService
    datalab_service: NaverDataLabService
    clustering_service: QueryClusteringService
    feature_service: FeatureExtractionService
    budget_allocator_service: BudgetAllocatorService
    collection_scheduler_service: CollectionSchedulerService
    collector_service: CollectorService
    google_search_service: GoogleSearchService
    google_collector_service: GoogleCollectorService
    scoring_service: ScoringService
    report_service: ReportService
    pipeline_service: PipelineService


@lru_cache(maxsize=1)
def get_container() -> ApplicationContainer:
    llm_service = OpenAIResearchService()
    datalab_service = NaverDataLabService()
    clustering_service = QueryClusteringService()
    feature_service = FeatureExtractionService()
    budget_allocator_service = BudgetAllocatorService()
    collection_scheduler_service = CollectionSchedulerService()
    google_search_service = GoogleSearchService()
    collector_service = CollectorService(
        datalab_service=datalab_service,
        feature_service=feature_service,
        budget_allocator=budget_allocator_service,
        collection_scheduler=collection_scheduler_service,
    )
    google_collector_service = GoogleCollectorService(
        google_search_service=google_search_service,
        budget_allocator=budget_allocator_service,
    )
    scoring_service = ScoringService()
    report_service = ReportService(llm_service=llm_service)
    pipeline_service = PipelineService(
        llm_service=llm_service,
        datalab_service=datalab_service,
        clustering_service=clustering_service,
        feature_service=feature_service,
        collection_scheduler_service=collection_scheduler_service,
        scoring_service=scoring_service,
        report_service=report_service,
    )
    return ApplicationContainer(
        llm_service=llm_service,
        datalab_service=datalab_service,
        clustering_service=clustering_service,
        feature_service=feature_service,
        budget_allocator_service=budget_allocator_service,
        collection_scheduler_service=collection_scheduler_service,
        collector_service=collector_service,
        google_search_service=google_search_service,
        google_collector_service=google_collector_service,
        scoring_service=scoring_service,
        report_service=report_service,
        pipeline_service=pipeline_service,
    )
