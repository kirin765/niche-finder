from dataclasses import dataclass
from functools import lru_cache

from micro_niche_finder.jobs.pipeline import PipelineService
from micro_niche_finder.services.budget_allocator_service import BudgetAllocatorService
from micro_niche_finder.services.collection_scheduler_service import CollectionSchedulerService
from micro_niche_finder.services.collector_service import CollectorService
from micro_niche_finder.services.clustering_service import QueryClusteringService
from micro_niche_finder.services.datalab_service import NaverDataLabService
from micro_niche_finder.services.daily_report_service import DailyReportService
from micro_niche_finder.services.feature_service import FeatureExtractionService
from micro_niche_finder.services.gmail_service import GmailService
from micro_niche_finder.services.google_collector_service import GoogleCollectorService
from micro_niche_finder.services.google_search_service import GoogleSearchService
from micro_niche_finder.services.kosis_collector_service import KosisCollectorService
from micro_niche_finder.services.kosis_employee_service import KosisEmployeeService
from micro_niche_finder.services.llm_service import OpenAIResearchService
from micro_niche_finder.services.naver_search_collector_service import NaverSearchCollectorService
from micro_niche_finder.services.naver_search_service import NaverSearchService
from micro_niche_finder.services.naver_shopping_insight_collector_service import (
    NaverShoppingInsightCollectorService,
)
from micro_niche_finder.services.naver_shopping_insight_service import NaverShoppingInsightService
from micro_niche_finder.services.public_data_opportunity_service import PublicDataOpportunityService
from micro_niche_finder.services.report_service import ReportService
from micro_niche_finder.services.scoring_service import ScoringService
from micro_niche_finder.services.telegram_service import TelegramService


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
    naver_search_service: NaverSearchService
    naver_search_collector_service: NaverSearchCollectorService
    naver_shopping_insight_service: NaverShoppingInsightService
    naver_shopping_insight_collector_service: NaverShoppingInsightCollectorService
    public_data_opportunity_service: PublicDataOpportunityService
    kosis_employee_service: KosisEmployeeService
    kosis_collector_service: KosisCollectorService
    scoring_service: ScoringService
    report_service: ReportService
    pipeline_service: PipelineService
    telegram_service: TelegramService
    gmail_service: GmailService
    daily_report_service: DailyReportService


@lru_cache(maxsize=1)
def get_container() -> ApplicationContainer:
    llm_service = OpenAIResearchService()
    datalab_service = NaverDataLabService()
    clustering_service = QueryClusteringService()
    feature_service = FeatureExtractionService()
    budget_allocator_service = BudgetAllocatorService()
    collection_scheduler_service = CollectionSchedulerService()
    google_search_service = GoogleSearchService()
    naver_search_service = NaverSearchService()
    naver_shopping_insight_service = NaverShoppingInsightService()
    public_data_opportunity_service = PublicDataOpportunityService()
    kosis_employee_service = KosisEmployeeService()
    telegram_service = TelegramService()
    gmail_service = GmailService()
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
    naver_search_collector_service = NaverSearchCollectorService(
        naver_search_service=naver_search_service,
        budget_allocator=budget_allocator_service,
    )
    naver_shopping_insight_collector_service = NaverShoppingInsightCollectorService(
        naver_shopping_insight_service=naver_shopping_insight_service,
        budget_allocator=budget_allocator_service,
    )
    kosis_collector_service = KosisCollectorService(
        kosis_employee_service=kosis_employee_service,
        budget_allocator=budget_allocator_service,
    )
    scoring_service = ScoringService()
    report_service = ReportService(llm_service=llm_service)
    pipeline_service = PipelineService(
        llm_service=llm_service,
        datalab_service=datalab_service,
        kosis_employee_service=kosis_employee_service,
        google_search_service=google_search_service,
        naver_search_service=naver_search_service,
        naver_shopping_insight_service=naver_shopping_insight_service,
        public_data_opportunity_service=public_data_opportunity_service,
        clustering_service=clustering_service,
        feature_service=feature_service,
        collection_scheduler_service=collection_scheduler_service,
        scoring_service=scoring_service,
        report_service=report_service,
    )
    daily_report_service = DailyReportService(
        pipeline_service=pipeline_service,
        telegram_service=telegram_service,
        gmail_service=gmail_service,
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
        naver_search_service=naver_search_service,
        naver_search_collector_service=naver_search_collector_service,
        naver_shopping_insight_service=naver_shopping_insight_service,
        naver_shopping_insight_collector_service=naver_shopping_insight_collector_service,
        public_data_opportunity_service=public_data_opportunity_service,
        kosis_employee_service=kosis_employee_service,
        kosis_collector_service=kosis_collector_service,
        scoring_service=scoring_service,
        report_service=report_service,
        pipeline_service=pipeline_service,
        telegram_service=telegram_service,
        gmail_service=gmail_service,
        daily_report_service=daily_report_service,
    )
