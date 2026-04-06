from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import GoogleCustomSearchResponse, GoogleSearchRequest, OnlineGTMContext
from micro_niche_finder.services.search_channel_classifier import SearchChannelClassifier, SearchResultDocument


class GoogleSearchService:
    SOURCE = "google_custom_search"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.channel_classifier = SearchChannelClassifier()
        self._runtime_disabled = False

    def is_configured(self) -> bool:
        return not self._runtime_disabled and bool(
            self.settings.google_custom_search_api_key and self.settings.google_custom_search_cx
        )

    @retry(
        wait=wait_exponential(min=1, max=8),
        stop=stop_after_attempt(3),
        retry=retry_if_exception(lambda exc: GoogleSearchService._should_retry(exc)),
        reraise=True,
    )
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
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if self._is_permission_error(exc):
                    self._runtime_disabled = True
                    return self._mock_response(request)
                raise
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

    def build_online_gtm_context(
        self,
        *,
        query: str,
        response: GoogleCustomSearchResponse,
        suggested_channels: list[str] | None = None,
    ) -> OnlineGTMContext:
        documents = [
            SearchResultDocument(
                title=item.title or "",
                link=item.link,
                snippet=item.snippet or "",
            )
            for item in response.items
        ]
        return self.channel_classifier.classify_documents(
            query=query,
            documents=documents,
            suggested_channels=suggested_channels,
        )

    @staticmethod
    def _is_permission_error(exc: httpx.HTTPStatusError) -> bool:
        return exc.response.status_code in {401, 403}

    @staticmethod
    def _should_retry(exc: Exception) -> bool:
        if isinstance(exc, httpx.HTTPStatusError):
            return not GoogleSearchService._is_permission_error(exc)
        return isinstance(exc, httpx.HTTPError)
