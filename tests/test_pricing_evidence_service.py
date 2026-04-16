from micro_niche_finder.domain.schemas import GoogleCustomSearchResponse
from micro_niche_finder.services.pricing_evidence_service import PricingEvidenceService


class _FakeGoogleSearchService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch(self, request):
        self.calls.append(request.q)
        return GoogleCustomSearchResponse.model_validate(
            {
                "searchInformation": {"totalResults": "3"},
                "items": [
                    {
                        "title": f"{request.q} Starter 요금 월 49000원",
                        "link": "https://example.com/pricing",
                        "snippet": "Basic 플랜 49000원/월, Pro 플랜 99000원/월",
                        "displayLink": "example.com",
                    }
                ],
            }
        )


def test_pricing_evidence_service_extracts_monthly_prices() -> None:
    google_search_service = _FakeGoogleSearchService()
    service = PricingEvidenceService(google_search_service=google_search_service)

    context = service.collect(canonical_name="학원 상담 관리", queries=["학원 상담 관리 프로그램"])

    assert context.pricing_page_count >= 1
    assert 49000 in context.detected_price_points_krw
    assert context.median_monthly_price_krw is not None
    assert "가격 흔적" in context.summary


def test_pricing_evidence_service_limits_searches_in_fast_mode() -> None:
    google_search_service = _FakeGoogleSearchService()
    service = PricingEvidenceService(google_search_service=google_search_service)

    context = service.collect(
        canonical_name="학원 상담 관리",
        queries=["학원 상담 관리 프로그램", "학원 상담 관리 솔루션"],
        max_search_queries=1,
        allow_page_fetch=False,
    )

    assert len(google_search_service.calls) == 1
    assert context.search_queries == ["학원 상담 관리 가격"]
