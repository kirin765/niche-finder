from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import GoogleCustomSearchResponse, GoogleSearchRequest


class GoogleSearchService:
    SOURCE = "google_custom_search"

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return bool(self.settings.google_custom_search_api_key and self.settings.google_custom_search_cx)

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
    def fetch(self, request: GoogleSearchRequest) -> GoogleCustomSearchResponse:
        if not self.is_configured():
            return self._mock_response(request)

        params = {
            "key": self.settings.google_custom_search_api_key,
            "cx": self.settings.google_custom_search_cx,
            "q": request.q,
            "num": request.num,
            "gl": request.gl,
            "hl": request.hl,
            "safe": request.safe,
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.get(self.settings.google_custom_search_base_url, params=params)
            response.raise_for_status()
        return GoogleCustomSearchResponse.model_validate(response.json())

    def _mock_response(self, request: GoogleSearchRequest) -> GoogleCustomSearchResponse:
        pseudo_total = max(10, min(5000, len(request.q) * 137))
        return GoogleCustomSearchResponse.model_validate(
            {
                "searchInformation": {"totalResults": str(pseudo_total)},
                "items": [
                    {
                        "title": f"{request.q} 가이드",
                        "link": "https://example.com/mock-guide",
                        "snippet": f"{request.q} 관련 운영 자동화와 관리 방법",
                        "displayLink": "example.com",
                    },
                    {
                        "title": f"{request.q} 프로그램 비교",
                        "link": "https://example.com/mock-tools",
                        "snippet": f"{request.q} 해결용 툴과 프로그램 비교",
                        "displayLink": "example.com",
                    },
                ],
            }
        )
