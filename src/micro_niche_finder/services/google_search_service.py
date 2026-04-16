from __future__ import annotations

import httpx

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import GoogleCustomSearchResponse, GoogleSearchRequest, OnlineGTMContext
from micro_niche_finder.services.brave_usage_budget_service import BraveUsageBudgetService
from micro_niche_finder.services.search_channel_classifier import SearchChannelClassifier, SearchResultDocument


class GoogleSearchService:
    SOURCE = "brave_search_web"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.channel_classifier = SearchChannelClassifier()
        self.brave_usage_budget_service = BraveUsageBudgetService()
        self._runtime_disabled = False

    def is_configured(self) -> bool:
        return not self._runtime_disabled and bool(self.settings.brave_search_api_key)

    def fetch(self, request: GoogleSearchRequest) -> GoogleCustomSearchResponse:
        if not self.is_configured():
            return self._mock_response(request)

        if not self.brave_usage_budget_service.consume_monthly_call():
            return self._mock_response(request)

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.settings.brave_search_api_key or "",
        }
        params = {
            "q": request.q,
            "count": request.num,
            "country": request.gl.upper(),
            "search_lang": request.hl,
        }
        with httpx.Client(timeout=20.0) as client:
            try:
                response = client.get(self.settings.brave_search_base_url, headers=headers, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if self._is_permission_error(exc) or self._is_rate_limit_error(exc) or self._is_quota_error(exc):
                    self._runtime_disabled = True
                return self._mock_response(request)
            except httpx.HTTPError:
                return self._mock_response(request)
        return self._transform_brave_response(response.json(), request=request)

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

    def _transform_brave_response(
        self,
        payload: dict,
        *,
        request: GoogleSearchRequest,
    ) -> GoogleCustomSearchResponse:
        web_results = payload.get("web", {}).get("results", [])
        items = [
            {
                "title": item.get("title"),
                "link": item.get("url"),
                "snippet": item.get("description"),
                "displayLink": item.get("meta_url", {}).get("netloc") or item.get("profile", {}).get("long_name"),
            }
            for item in web_results[: request.num]
        ]
        total_results = len(web_results)
        if payload.get("query", {}).get("more_results_available"):
            total_results = max(total_results, request.num + 1)
        return GoogleCustomSearchResponse.model_validate(
            {
                "searchInformation": {"totalResults": str(total_results)},
                "items": items,
            }
        )

    @staticmethod
    def _is_permission_error(exc: httpx.HTTPStatusError) -> bool:
        return exc.response.status_code in {401, 403}

    @staticmethod
    def _is_rate_limit_error(exc: httpx.HTTPStatusError) -> bool:
        return exc.response.status_code == 429

    @staticmethod
    def _is_quota_error(exc: httpx.HTTPStatusError) -> bool:
        return exc.response.status_code == 402
