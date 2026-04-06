from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from micro_niche_finder.config.database import Base
from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.models import FinalReport, NicheScore, QueryGroup, SeedCategory
from micro_niche_finder.jobs.pipeline import PipelineService
from micro_niche_finder.services.clustering_service import QueryClusteringService
from micro_niche_finder.services.collection_scheduler_service import CollectionSchedulerService
from micro_niche_finder.services.datalab_service import NaverDataLabService
from micro_niche_finder.services.feature_service import FeatureExtractionService
from micro_niche_finder.services.google_search_service import GoogleSearchService
from micro_niche_finder.services.kosis_employee_service import KosisEmployeeService
from micro_niche_finder.services.llm_service import OpenAIResearchService
from micro_niche_finder.services.naver_ads_keyword_service import NaverAdsKeywordService
from micro_niche_finder.services.naver_search_service import NaverSearchService
from micro_niche_finder.services.naver_shopping_insight_service import NaverShoppingInsightService
from micro_niche_finder.services.pricing_evidence_service import PricingEvidenceService
from micro_niche_finder.services.public_data_opportunity_service import PublicDataOpportunityService
from micro_niche_finder.services.report_service import ReportService
from micro_niche_finder.services.scoring_service import ScoringService


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def test_pipeline_end_to_end_generates_reports_with_mocked_services(monkeypatch) -> None:
    for env_name in (
        "OPENAI_API_KEY",
        "NAVER_DATALAB_CLIENT_ID",
        "NAVER_DATALAB_CLIENT_SECRET",
        "NAVER_SEARCH_CLIENT_ID",
        "NAVER_SEARCH_CLIENT_SECRET",
        "NAVER_DATALAB_CLIENT_ID",
        "NAVER_DATALAB_CLIENT_SECRET",
        "BRAVE_SEARCH_API_KEY",
        "KOSIS_API_KEY",
        "NAVER_ADS_CUSTOMER_ID",
        "NAVER_ADS_API_KEY",
        "NAVER_ADS_SECRET_KEY",
    ):
        monkeypatch.setenv(env_name, "")
    get_settings.cache_clear()

    session = _build_session()
    seed = SeedCategory(name="학원 운영", description="학원 운영 반복업무")
    session.add(seed)
    session.commit()

    llm_service = OpenAIResearchService()
    google_search_service = GoogleSearchService()
    pipeline = PipelineService(
        llm_service=llm_service,
        datalab_service=NaverDataLabService(),
        kosis_employee_service=KosisEmployeeService(),
        google_search_service=google_search_service,
        naver_search_service=NaverSearchService(),
        naver_ads_keyword_service=NaverAdsKeywordService(),
        naver_shopping_insight_service=NaverShoppingInsightService(),
        pricing_evidence_service=PricingEvidenceService(google_search_service=google_search_service),
        public_data_opportunity_service=PublicDataOpportunityService(),
        clustering_service=QueryClusteringService(),
        feature_service=FeatureExtractionService(),
        collection_scheduler_service=CollectionSchedulerService(),
        scoring_service=ScoringService(),
        report_service=ReportService(llm_service=llm_service),
    )

    result = pipeline.run(session=session, seed_category_id=seed.id, candidate_count=5, top_k=2)
    session.commit()

    assert result.generated_candidates == 5
    assert result.scored_candidates == 5
    assert result.reported_candidates == 2
    assert len(result.reports) == 2
    assert result.reports[0].niche_name
    assert session.scalar(select(QueryGroup.id)) is not None
    assert session.scalar(select(NicheScore.id)) is not None
    assert session.scalar(select(FinalReport.id)) is not None

