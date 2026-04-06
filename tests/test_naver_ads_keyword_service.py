from micro_niche_finder.domain.schemas import KeywordVolumeRequest
from micro_niche_finder.services.naver_ads_keyword_service import NaverAdsKeywordService


def test_naver_ads_keyword_service_mock_builds_absolute_demand_context() -> None:
    service = NaverAdsKeywordService()
    request = KeywordVolumeRequest(keywords=["학원 상담 관리", "학원 CRM"])

    metrics = service.fetch(request)
    context = service.build_context(keywords=request.keywords, metrics=metrics)

    assert len(metrics) == 2
    assert context.max_monthly_searches is not None
    assert context.average_monthly_searches is not None
    assert "월간 검색량" in context.summary

