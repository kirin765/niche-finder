from dataclasses import dataclass
from functools import lru_cache

from micro_niche_finder.jobs.pipeline import PipelineService
from micro_niche_finder.services.brainstorming_v2_service import BrainstormingV2Service
from micro_niche_finder.services.budget_allocator_service import BudgetAllocatorService
from micro_niche_finder.services.collection_scheduler_service import CollectionSchedulerService
from micro_niche_finder.services.collector_service import CollectorService
from micro_niche_finder.services.clustering_service import QueryClusteringService
from micro_niche_finder.services.datalab_service import NaverDataLabService
from micro_niche_finder.services.feature_service import FeatureExtractionService
from micro_niche_finder.services.gmail_service import GmailService
from micro_niche_finder.services.google_collector_service import GoogleCollectorService
from micro_niche_finder.services.improvement_discovery_service import ImprovementDiscoveryService
from micro_niche_finder.services.google_search_service import GoogleSearchService
from micro_niche_finder.services.kosis_collector_service import KosisCollectorService
from micro_niche_finder.services.kosis_employee_service import KosisEmployeeService
from micro_niche_finder.services.llm_service import OpenAIResearchService
from micro_niche_finder.services.naver_ads_keyword_service import NaverAdsKeywordService
from micro_niche_finder.services.naver_search_collector_service import NaverSearchCollectorService
from micro_niche_finder.services.naver_search_service import NaverSearchService
from micro_niche_finder.services.naver_shopping_insight_collector_service import (
    NaverShoppingInsightCollectorService,
)
from micro_niche_finder.services.naver_shopping_insight_service import NaverShoppingInsightService
from micro_niche_finder.services.pricing_evidence_service import PricingEvidenceService
from micro_niche_finder.services.public_data_opportunity_service import PublicDataOpportunityService
from micro_niche_finder.services.report_service import ReportService
from micro_niche_finder.services.scoring_service import ScoringService
from micro_niche_finder.services.seedless_v2_service import SeedlessV2Service
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
    naver_ads_keyword_service: NaverAdsKeywordService
    naver_search_collector_service: NaverSearchCollectorService
    naver_shopping_insight_service: NaverShoppingInsightService
    naver_shopping_insight_collector_service: NaverShoppingInsightCollectorService
    pricing_evidence_service: PricingEvidenceService
    public_data_opportunity_service: PublicDataOpportunityService
    kosis_employee_service: KosisEmployeeService
    kosis_collector_service: KosisCollectorService
    scoring_service: ScoringService
    report_service: ReportService
    pipeline_service: PipelineService
    telegram_service: TelegramService
    gmail_service: GmailService
    brainstorming_v2_service: BrainstormingV2Service
    improvement_discovery_service: ImprovementDiscoveryService
    seedless_v2_service: SeedlessV2Service


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
    naver_ads_keyword_service = NaverAdsKeywordService()
    naver_shopping_insight_service = NaverShoppingInsightService()
    pricing_evidence_service = PricingEvidenceService(google_search_service=google_search_service)
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
    brainstorming_v2_service = BrainstormingV2Service(report_service=report_service)
    pipeline_service = PipelineService(
        llm_service=llm_service,
        datalab_service=datalab_service,
        kosis_employee_service=kosis_employee_service,
        google_search_service=google_search_service,
        naver_search_service=naver_search_service,
        naver_ads_keyword_service=naver_ads_keyword_service,
        naver_shopping_insight_service=naver_shopping_insight_service,
        pricing_evidence_service=pricing_evidence_service,
        public_data_opportunity_service=public_data_opportunity_service,
        clustering_service=clustering_service,
        feature_service=feature_service,
        collection_scheduler_service=collection_scheduler_service,
        scoring_service=scoring_service,
        report_service=report_service,
        brainstorming_v2_service=brainstorming_v2_service,
    )
    improvement_discovery_service = ImprovementDiscoveryService(
        google_search_service=google_search_service,
        telegram_service=telegram_service,
    )
    seedless_v2_service = SeedlessV2Service(
        naver_search_service=naver_search_service,
        google_search_service=google_search_service,
        pricing_evidence_service=pricing_evidence_service,
        public_data_opportunity_service=public_data_opportunity_service,
        telegram_service=telegram_service,
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
        naver_ads_keyword_service=naver_ads_keyword_service,
        naver_search_collector_service=naver_search_collector_service,
        naver_shopping_insight_service=naver_shopping_insight_service,
        naver_shopping_insight_collector_service=naver_shopping_insight_collector_service,
        pricing_evidence_service=pricing_evidence_service,
        public_data_opportunity_service=public_data_opportunity_service,
        kosis_employee_service=kosis_employee_service,
        kosis_collector_service=kosis_collector_service,
        scoring_service=scoring_service,
        report_service=report_service,
        pipeline_service=pipeline_service,
        telegram_service=telegram_service,
        gmail_service=gmail_service,
        brainstorming_v2_service=brainstorming_v2_service,
        improvement_discovery_service=improvement_discovery_service,
        seedless_v2_service=seedless_v2_service,
    )
