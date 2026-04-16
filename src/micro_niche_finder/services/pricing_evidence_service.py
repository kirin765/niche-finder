from __future__ import annotations

import re
from statistics import median

import httpx

from micro_niche_finder.domain.schemas import GoogleSearchRequest, GoogleSearchResultItem, PricingEvidenceContext
from micro_niche_finder.services.google_search_service import GoogleSearchService


class PricingEvidenceService:
    SOURCE = "brave_pricing_evidence"
    SOURCE_LABEL = "Brave pricing evidence"

    def __init__(self, google_search_service: GoogleSearchService) -> None:
        self.google_search_service = google_search_service

    def collect(
        self,
        *,
        canonical_name: str,
        queries: list[str],
        max_search_queries: int = 3,
        allow_page_fetch: bool = True,
    ) -> PricingEvidenceContext:
        search_queries = self._build_queries(canonical_name, queries)
        search_queries = search_queries[: max(0, max_search_queries)]
        price_points: list[int] = []
        pricing_page_count = 0

        for query in search_queries:
            response = self.google_search_service.fetch(GoogleSearchRequest(q=query, num=5))
            for item in response.items:
                text = " ".join(part for part in [item.title or "", item.snippet or ""] if part)
                extracted = self._extract_prices_krw(text)
                if extracted:
                    price_points.extend(extracted)
                    pricing_page_count += 1
                elif allow_page_fetch and self._looks_like_pricing_page(item):
                    fetched = self._fetch_page_text(item.link)
                    extracted = self._extract_prices_krw(fetched)
                    if extracted:
                        price_points.extend(extracted)
                        pricing_page_count += 1

        normalized = sorted(set(value for value in price_points if 5_000 <= value <= 5_000_000))
        median_price = int(median(normalized)) if normalized else None
        max_price = max(normalized) if normalized else None

        if median_price is not None:
            summary = (
                f"유사 솔루션 가격 흔적은 월 약 {median_price:,}원 수준이 중심이며, "
                f"확인된 가격 페이지는 {pricing_page_count}건이다."
            )
        else:
            summary = "유사 솔루션의 공개 가격 흔적은 아직 충분히 확인되지 않았다."

        return PricingEvidenceContext(
            source=self.SOURCE,
            source_label=self.SOURCE_LABEL,
            search_queries=search_queries,
            pricing_page_count=pricing_page_count,
            detected_price_points_krw=normalized[:12],
            median_monthly_price_krw=median_price,
            max_monthly_price_krw=max_price,
            summary=summary,
        )

    def _build_queries(self, canonical_name: str, queries: list[str]) -> list[str]:
        base_queries = [canonical_name, *queries[:2]]
        enriched = []
        for query in base_queries:
            cleaned = " ".join(query.split()).strip()
            if not cleaned:
                continue
            enriched.extend([f"{cleaned} 가격", f"{cleaned} 요금", f"{cleaned} 프로그램 가격"])
        return list(dict.fromkeys(enriched))[:3]

    @staticmethod
    def _looks_like_pricing_page(item: GoogleSearchResultItem) -> bool:
        text = " ".join(part for part in [item.title or "", item.snippet or "", item.link or ""] if part).lower()
        return any(marker in text for marker in ("pricing", "price", "요금", "가격", "plan", "plans", "/pricing"))

    @staticmethod
    def _fetch_page_text(link: str | None) -> str:
        if not link:
            return ""
        try:
            with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                response = client.get(link)
                response.raise_for_status()
            return response.text[:50000]
        except Exception:
            return ""

    @staticmethod
    def _extract_prices_krw(text: str) -> list[int]:
        normalized = text.replace(",", "").replace(" ", "")
        prices: list[int] = []
        for match in re.finditer(r"(\d{1,4})(?:\.\d+)?만원", normalized, flags=re.IGNORECASE):
            prices.append(int(float(match.group(1)) * 10_000))
        for match in re.finditer(r"(\d{4,7})원", normalized, flags=re.IGNORECASE):
            prices.append(int(match.group(1)))

        monthly_only: list[int] = []
        lowered = normalized.lower()
        for value in prices:
            text_value = str(value)
            patterns = (
                f"월{text_value}",
                f"{text_value}원/월",
                f"{text_value}원월",
                f"{text_value}원/month",
                f"{text_value}원monthly",
            )
            if any(pattern in lowered for pattern in patterns):
                monthly_only.append(value)
        return monthly_only or prices
