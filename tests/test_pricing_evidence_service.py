from micro_niche_finder.domain.schemas import GoogleCustomSearchResponse
from micro_niche_finder.services.pricing_evidence_service import PricingEvidenceService


class _FakeGoogleSearchService:
    def fetch(self, request):
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
    service = PricingEvidenceService(google_search_service=_FakeGoogleSearchService())

    context = service.collect(canonical_name="학원 상담 관리", queries=["학원 상담 관리 프로그램"])

    assert context.pricing_page_count >= 1
    assert 49000 in context.detected_price_points_krw
    assert context.median_monthly_price_krw is not None
    assert "가격 흔적" in context.summary

