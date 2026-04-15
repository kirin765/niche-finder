from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import KeywordVolumeRequest
from micro_niche_finder.services.naver_ads_keyword_service import NaverAdsKeywordService


def test_naver_ads_keyword_service_mock_builds_absolute_demand_context(monkeypatch) -> None:
    monkeypatch.setenv("NAVER_ADS_CUSTOMER_ID", "")
    monkeypatch.setenv("NAVER_ADS_API_KEY", "")
    monkeypatch.setenv("NAVER_ADS_SECRET_KEY", "")
    get_settings.cache_clear()


def test_naver_ads_keyword_service_build_request_strips_spaces() -> None:
    service = NaverAdsKeywordService()

    request = service.build_request(["학원 상담 관리", "학원 CRM", " 학원   상담   관리 "])

    assert request.keywords == ["학원상담관리", "학원CRM"]

    service = NaverAdsKeywordService()
    request = KeywordVolumeRequest(keywords=["학원 상담 관리", "학원 CRM"])

    metrics = service.fetch(request)
    context = service.build_context(keywords=request.keywords, metrics=metrics)

    assert len(metrics) == 2
    assert context.max_monthly_searches is not None
    assert context.average_monthly_searches is not None
    assert "월간 검색량" in context.summary

    get_settings.cache_clear()
