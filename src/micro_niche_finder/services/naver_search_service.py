from __future__ import annotations

import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import NaverSearchRequest, NaverSearchResponse, OnlineGTMContext, SearchEvidenceContext
from micro_niche_finder.services.search_channel_classifier import SearchChannelClassifier, SearchResultDocument


class NaverSearchService:
    SOURCE = "naver_search_webkr"
    SOURCE_LABEL = "Naver Search Web"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.channel_classifier = SearchChannelClassifier()

    def credentials(self) -> tuple[str | None, str | None]:
        client_id = self.settings.naver_search_client_id or self.settings.naver_datalab_client_id
        client_secret = self.settings.naver_search_client_secret or self.settings.naver_datalab_client_secret
        return client_id, client_secret

    def is_configured(self) -> bool:
        client_id, client_secret = self.credentials()
        return bool(client_id and client_secret)

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
    def fetch(self, request: NaverSearchRequest) -> NaverSearchResponse:
        if not self.is_configured():
            return self._mock_response(request)

        client_id, client_secret = self.credentials()
        headers = {
            "X-Naver-Client-Id": client_id or "",
            "X-Naver-Client-Secret": client_secret or "",
        }
        params = {
            "query": request.query,
            "display": request.display,
            "start": request.start,
            "sort": request.sort,
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.get(self.settings.naver_search_base_url, headers=headers, params=params)
            response.raise_for_status()
        return NaverSearchResponse.model_validate(response.json())

    def build_search_evidence(self, *, query: str, response: NaverSearchResponse) -> SearchEvidenceContext:
        top_titles = [self._clean_text(item.title) for item in response.items[:3] if item.title]
        if response.total:
            summary = f"네이버 웹검색에서 '{query}' 관련 결과는 약 {response.total:,}건이며, 상위 문서 주제는 {', '.join(top_titles) if top_titles else '확인 가능'} 수준이다."
        else:
            summary = f"네이버 웹검색에서 '{query}' 관련 결과 수는 제한적이거나 확인되지 않았다."
        return SearchEvidenceContext(
            source=self.SOURCE,
            source_label=self.SOURCE_LABEL,
            query=query,
            total_results=response.total,
            top_titles=top_titles,
            summary=summary,
        )

    def build_online_gtm_context(
        self,
        *,
        query: str,
        response: NaverSearchResponse,
        suggested_channels: list[str] | None = None,
    ) -> OnlineGTMContext:
        documents = [
            SearchResultDocument(
                title=self._clean_text(item.title),
                link=item.link,
                snippet=self._clean_text(item.description or ""),
            )
            for item in response.items
        ]
        return self.channel_classifier.classify_documents(
            query=query,
            documents=documents,
            suggested_channels=suggested_channels,
        )

    def _mock_response(self, request: NaverSearchRequest) -> NaverSearchResponse:
        total = max(50, min(100000, len(request.query) * 321))
        return NaverSearchResponse.model_validate(
            {
                "total": total,
                "start": request.start,
                "display": request.display,
                "items": [
                    {
                        "title": f"{request.query} 운영 가이드",
                        "link": "https://example.com/naver-search-guide",
                        "description": f"{request.query} 관련 운영 노하우와 도구 비교",
                    },
                    {
                        "title": f"{request.query} 프로그램 추천",
                        "link": "https://example.com/naver-search-tools",
                        "description": f"{request.query} 자동화 프로그램 탐색 결과",
                    },
                ],
            }
        )

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"<[^>]+>", "", value).strip()
