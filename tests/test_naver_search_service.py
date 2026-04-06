from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import NaverSearchRequest, NaverSearchResponse
from micro_niche_finder.services.naver_search_service import NaverSearchService


def test_naver_search_service_mock_fallback_returns_shape(monkeypatch) -> None:
    monkeypatch.setenv("NAVER_SEARCH_CLIENT_ID", "")
    monkeypatch.setenv("NAVER_SEARCH_CLIENT_SECRET", "")
    monkeypatch.setenv("NAVER_DATALAB_CLIENT_ID", "")
    monkeypatch.setenv("NAVER_DATALAB_CLIENT_SECRET", "")
    get_settings.cache_clear()

    service = NaverSearchService()
    response = service.fetch(NaverSearchRequest(query="학원 상담 관리", display=3))

    assert response.total > 0
    assert len(response.items) >= 1

    get_settings.cache_clear()


def test_build_search_evidence_cleans_titles() -> None:
    service = NaverSearchService()
    response = NaverSearchResponse.model_validate(
        {
            "total": 1234,
            "display": 2,
            "items": [
                {"title": "<b>학원 상담 관리</b> 솔루션", "link": "https://example.com/1"},
                {"title": "<b>학원 CRM</b> 비교", "link": "https://example.com/2"},
            ],
        }
    )

    evidence = service.build_search_evidence(query="학원 상담 관리", response=response)

    assert evidence.total_results == 1234
    assert evidence.top_titles == ["학원 상담 관리 솔루션", "학원 CRM 비교"]
    assert "1,234건" in evidence.summary
