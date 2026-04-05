from micro_niche_finder.domain.schemas import GoogleSearchRequest
from micro_niche_finder.services.google_search_service import GoogleSearchService


def test_google_search_service_mock_fallback_returns_shape() -> None:
    service = GoogleSearchService()
    response = service.fetch(GoogleSearchRequest(q="스마트스토어 경쟁사 가격 확인", num=3))
    assert int(response.searchInformation.totalResults) > 0
    assert len(response.items) >= 1
