import httpx

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import GoogleCustomSearchResponse, GoogleSearchRequest
from micro_niche_finder.services.google_search_service import GoogleSearchService


def test_google_search_service_mock_fallback_returns_shape(monkeypatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "")
    get_settings.cache_clear()

    service = GoogleSearchService()
    response = service.fetch(GoogleSearchRequest(q="스마트스토어 경쟁사 가격 확인", num=3))
    assert int(response.searchInformation.totalResults) > 0
    assert len(response.items) >= 1

    get_settings.cache_clear()


def test_google_search_service_builds_online_gtm_context() -> None:
    service = GoogleSearchService()
    response = GoogleCustomSearchResponse.model_validate(
        {
            "searchInformation": {"totalResults": "321"},
            "items": [
                {
                    "title": "스마트스토어 셀러 커뮤니티 추천 툴",
                    "link": "https://forum.example.com/post/1",
                    "snippet": "커뮤니티에서 추천한 운영 도구",
                    "displayLink": "forum.example.com",
                },
                {
                    "title": "스마트스토어 정산 프로그램 비교",
                    "link": "https://saas.example.com/store-settlement",
                    "snippet": "프로그램 비교와 자동화 기능",
                    "displayLink": "saas.example.com",
                },
            ],
        }
    )

    context = service.build_online_gtm_context(
        query="스마트스토어 정산 관리",
        response=response,
        suggested_channels=["블로그 SEO"],
    )

    assert context.channel_counts["community"] == 1
    assert context.channel_counts["competitor"] == 1
    assert "블로그 SEO" in context.channel_signals
    assert context.competitor_presence_score == 0.5
    assert context.competitor_domains == ["saas.example.com"]
    assert context.competitive_whitespace_score == 0.4875


def test_google_search_service_falls_back_on_permission_error(monkeypatch) -> None:
    class _DeniedClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, *args, **kwargs):
            request = httpx.Request("GET", "https://customsearch.googleapis.com/customsearch/v1")
            return httpx.Response(
                403,
                request=request,
                json={
                    "error": {
                        "code": 403,
                        "message": "This project does not have the access to Custom Search JSON API.",
                    }
                },
            )

    monkeypatch.setattr(httpx, "Client", _DeniedClient)
    get_settings.cache_clear()

    service = GoogleSearchService()
    response = service.fetch(GoogleSearchRequest(q="학원 상담 관리", num=3))

    assert int(response.searchInformation.totalResults) > 0
    assert service.is_configured() is False


def test_google_search_service_falls_back_on_rate_limit(monkeypatch) -> None:
    class _RateLimitedClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, *args, **kwargs):
            request = httpx.Request("GET", "https://api.search.brave.com/res/v1/web/search")
            return httpx.Response(
                429,
                request=request,
                json={
                    "error": {
                        "code": 429,
                        "message": "Rate limit exceeded.",
                    }
                },
            )

    monkeypatch.setattr(httpx, "Client", _RateLimitedClient)
    get_settings.cache_clear()

    service = GoogleSearchService()
    response = service.fetch(GoogleSearchRequest(q="학원 상담 관리", num=3))

    assert int(response.searchInformation.totalResults) > 0
    assert service.is_configured() is False

    get_settings.cache_clear()


def test_google_search_service_transforms_brave_response() -> None:
    service = GoogleSearchService()
    response = service._transform_brave_response(
        {
            "query": {"more_results_available": True},
            "web": {
                "results": [
                    {
                        "title": "통통통 | 학원관리프로그램 전문 솔루션",
                        "url": "https://www.tongtongtong.co.kr/",
                        "description": "학원 운영을 한 번에 관리하는 솔루션",
                        "meta_url": {"netloc": "tongtongtong.co.kr"},
                    },
                    {
                        "title": "학원 상담 관리 가이드",
                        "url": "https://blog.example.com/academy-guide",
                        "description": "운영 가이드",
                        "meta_url": {"netloc": "blog.example.com"},
                    },
                ]
            },
        },
        request=GoogleSearchRequest(q="학원 상담 관리", num=3),
    )

    assert response.searchInformation.totalResults == "4"
    assert response.items[0].link == "https://www.tongtongtong.co.kr/"
    assert response.items[0].displayLink == "tongtongtong.co.kr"
