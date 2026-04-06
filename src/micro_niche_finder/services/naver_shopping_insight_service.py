from __future__ import annotations

import json
from datetime import date, timedelta
from math import sin

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import (
    NaverShoppingCategoryOption,
    NaverShoppingCategorySelection,
    NaverShoppingInsightPoint,
    NaverShoppingInsightRequest,
    NaverShoppingInsightResponse,
    ShoppingEvidenceContext,
)


class NaverShoppingInsightService:
    SOURCE = "naver_shopping_insight"
    SOURCE_LABEL = "Naver Shopping Insight"

    def __init__(self) -> None:
        self.settings = get_settings()

    def credentials(self) -> tuple[str | None, str | None]:
        return self.settings.naver_datalab_client_id, self.settings.naver_datalab_client_secret

    def is_configured(self) -> bool:
        client_id, client_secret = self.credentials()
        return bool(client_id and client_secret and self.settings.naver_shopping_category_options_json)

    def category_options(self) -> list[NaverShoppingCategoryOption]:
        if not self.settings.naver_shopping_category_options_json:
            return []
        payload = json.loads(self.settings.naver_shopping_category_options_json)
        return [NaverShoppingCategoryOption.model_validate(item) for item in payload]

    def is_relevant_niche(
        self,
        *,
        canonical_name: str,
        persona: str,
        problem_summary: str,
        query_group: list[str],
    ) -> bool:
        text = " ".join([canonical_name, persona, problem_summary, *query_group]).lower()
        positive = (
            "스마트스토어",
            "쇼핑몰",
            "셀러",
            "상품",
            "쿠팡",
            "네이버쇼핑",
            "판매",
            "리뷰",
            "가격",
            "재고",
            "발주",
            "배달",
            "소매",
            "이커머스",
        )
        negative = (
            "학원",
            "crm",
            "erp",
            "그룹웨어",
            "미수금",
            "청구",
            "예약",
            "출결",
            "상담",
            "인사",
            "회계",
            "b2b 서비스",
        )
        positive_hits = sum(1 for marker in positive if marker in text)
        negative_hits = sum(1 for marker in negative if marker in text)
        return positive_hits > 0 and positive_hits >= negative_hits

    def build_request(
        self,
        selection: NaverShoppingCategorySelection,
        *,
        weeks: int = 12,
        time_unit: str = "week",
    ) -> NaverShoppingInsightRequest:
        end_date = date.today()
        start_date = end_date - timedelta(weeks=weeks)
        return NaverShoppingInsightRequest(
            startDate=start_date,
            endDate=end_date,
            timeUnit=time_unit,
            category=[{"name": selection.label, "param": [selection.code]}],
        )

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
    def fetch(self, request: NaverShoppingInsightRequest) -> NaverShoppingInsightResponse:
        if not self.is_configured():
            return self._mock_response(request)

        client_id, client_secret = self.credentials()
        headers = {
            "X-Naver-Client-Id": client_id or "",
            "X-Naver-Client-Secret": client_secret or "",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                self.settings.naver_shopping_insight_base_url,
                headers=headers,
                json=request.model_dump(mode="json", exclude_none=True),
            )
            response.raise_for_status()
        return NaverShoppingInsightResponse.model_validate(response.json())

    def build_shopping_evidence(
        self,
        *,
        selection: NaverShoppingCategorySelection,
        response: NaverShoppingInsightResponse,
    ) -> ShoppingEvidenceContext:
        points = response.results[0].data if response.results else []
        recent_ratio = points[-1].ratio if points else None
        peak_ratio = max((point.ratio for point in points), default=None)
        summary = (
            f"네이버 쇼핑인사이트 기준 {selection.label} 카테고리의 최근 {response.timeUnit} 단위 추이는 "
            f"최근값 {recent_ratio:.1f}, 최고값 {peak_ratio:.1f} 수준이다."
            if recent_ratio is not None and peak_ratio is not None
            else f"네이버 쇼핑인사이트에서 {selection.label} 카테고리 추이를 확인했지만 유효한 수치를 추출하지 못했다."
        )
        return ShoppingEvidenceContext(
            source=self.SOURCE,
            source_label=self.SOURCE_LABEL,
            category_code=selection.code,
            category_label=selection.label,
            reference_window=f"{response.startDate.isoformat()}~{response.endDate.isoformat()}",
            recent_ratio=recent_ratio,
            peak_ratio=peak_ratio,
            summary=summary,
        )

    def _mock_response(self, request: NaverShoppingInsightRequest) -> NaverShoppingInsightResponse:
        points: list[NaverShoppingInsightPoint] = []
        current = request.startDate
        index = 0
        while current <= request.endDate:
            baseline = 55 + (index * 1.2)
            seasonal = 6 * sin(index / 2.2)
            points.append(NaverShoppingInsightPoint(period=current, ratio=round(max(5.0, baseline + seasonal), 2)))
            current += timedelta(weeks=1)
            index += 1
        return NaverShoppingInsightResponse(
            startDate=request.startDate,
            endDate=request.endDate,
            timeUnit=request.timeUnit,
            results=[
                {
                    "title": request.category[0].name,
                    "category": request.category[0].param,
                    "data": points,
                }
            ],
        )
