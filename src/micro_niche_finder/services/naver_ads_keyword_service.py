from __future__ import annotations

import base64
import hashlib
import hmac
import re
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import AbsoluteDemandContext, KeywordVolumeMetric, KeywordVolumeRequest


class NaverAdsKeywordService:
    SOURCE = "naver_ads_keyword_volume"
    SOURCE_LABEL = "Naver Ads Keyword Tool"

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return bool(
            self.settings.naver_ads_customer_id
            and self.settings.naver_ads_api_key
            and self.settings.naver_ads_secret_key
        )

    def build_request(self, keywords: list[str], *, limit: int = 5) -> KeywordVolumeRequest:
        cleaned = list(
            dict.fromkeys(
                re.sub(r"\s+", "", keyword.strip())
                for keyword in keywords
                if re.sub(r"\s+", "", keyword.strip())
            )
        )
        return KeywordVolumeRequest(keywords=cleaned[:limit])

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
    def fetch(self, request: KeywordVolumeRequest) -> list[KeywordVolumeMetric]:
        if not self.is_configured():
            return self._mock_response(request)

        sanitized_request = self.build_request(request.keywords, limit=len(request.keywords) or 5)
        timestamp = str(int(time.time() * 1000))
        uri = "/keywordstool"
        signature = base64.b64encode(
            hmac.new(
                (self.settings.naver_ads_secret_key or "").encode("utf-8"),
                f"{timestamp}.GET.{uri}".encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")
        headers = {
            "X-Timestamp": timestamp,
            "X-API-KEY": self.settings.naver_ads_api_key or "",
            "X-Customer": self.settings.naver_ads_customer_id or "",
            "X-Signature": signature,
        }
        params = {
            "hintKeywords": ",".join(sanitized_request.keywords),
            "showDetail": 1,
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.get(self.settings.naver_ads_base_url, headers=headers, params=params)
            response.raise_for_status()
        payload = response.json()
        metrics = [
            KeywordVolumeMetric(
                keyword=item.get("relKeyword") or "",
                monthly_pc_searches=self._to_int(item.get("monthlyPcQcCnt")),
                monthly_mobile_searches=self._to_int(item.get("monthlyMobileQcCnt")),
                monthly_total_searches=(
                    (self._to_int(item.get("monthlyPcQcCnt")) or 0) + (self._to_int(item.get("monthlyMobileQcCnt")) or 0)
                ),
                competition_index=item.get("compIdx"),
            )
            for item in payload.get("keywordList", [])
        ]
        exact_keywords = set(sanitized_request.keywords)
        exact_metrics = [item for item in metrics if item.keyword in exact_keywords]
        return exact_metrics or metrics

    def build_context(self, *, keywords: list[str], metrics: list[KeywordVolumeMetric]) -> AbsoluteDemandContext:
        totals = [item.monthly_total_searches for item in metrics if item.monthly_total_searches is not None]
        max_total = max(totals) if totals else None
        avg_total = int(sum(totals) / len(totals)) if totals else None
        if max_total is not None:
            summary = (
                f"네이버 검색광고 기준 월간 검색량은 최대 약 {max_total:,}, 평균 약 {avg_total:,} 수준으로 추정된다."
            )
        else:
            summary = "네이버 검색광고 절대 검색량은 아직 확인되지 않았다."
        return AbsoluteDemandContext(
            source=self.SOURCE,
            source_label=self.SOURCE_LABEL,
            keywords=keywords,
            max_monthly_searches=max_total,
            average_monthly_searches=avg_total,
            keyword_metrics=metrics,
            summary=summary,
        )

    def _mock_response(self, request: KeywordVolumeRequest) -> list[KeywordVolumeMetric]:
        metrics: list[KeywordVolumeMetric] = []
        for index, keyword in enumerate(request.keywords, start=1):
            total = max(40, min(12000, len(keyword.replace(" ", "")) * 85 + (index * 120)))
            pc = int(total * 0.35)
            mobile = total - pc
            metrics.append(
                KeywordVolumeMetric(
                    keyword=keyword,
                    monthly_pc_searches=pc,
                    monthly_mobile_searches=mobile,
                    monthly_total_searches=total,
                    competition_index="medium" if total > 1000 else "low",
                )
            )
        return metrics

    @staticmethod
    def _to_int(value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        if text.startswith("<"):
            digits = "".join(character for character in text if character.isdigit())
            return max(1, int(digits) - 1) if digits else 1
        digits = "".join(character for character in text if character.isdigit())
        return int(digits) if digits else None
