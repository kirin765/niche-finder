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


def test_build_online_gtm_context_classifies_search_channels() -> None:
    service = NaverSearchService()
    response = NaverSearchResponse.model_validate(
        {
            "total": 456,
            "display": 4,
            "items": [
                {
                    "title": "학원 원장 커뮤니티에서 본 상담 관리 툴",
                    "link": "https://cafe.naver.com/hakwonowners/1",
                    "description": "커뮤니티 후기",
                },
                {
                    "title": "학원 상담 관리 프로그램 비교",
                    "link": "https://crm-example.com/academy",
                    "description": "솔루션 비교",
                },
                {
                    "title": "학원 상담 운영 가이드",
                    "link": "https://blog.naver.com/example/1",
                    "description": "운영 방법 정리",
                },
                {
                    "title": "학원 운영 지원사업 안내",
                    "link": "https://www.gov.kr/portal/service/123",
                    "description": "정부 지원사업",
                },
            ],
        }
    )

    context = service.build_online_gtm_context(
        query="학원 상담 관리",
        response=response,
        suggested_channels=["네이버 검색"],
    )

    assert context.channel_counts["community"] == 1
    assert context.channel_counts["competitor"] == 1
    assert context.channel_counts["blog_content"] == 1
    assert context.channel_counts["government"] == 1
    assert "네이버 검색" in context.channel_signals
    assert context.community_presence_score == 0.25
    assert context.competitor_domains == ["crm-example.com"]
    assert context.brand_concentration_score == 1.0
    assert context.competitive_whitespace_score == 0.6375
