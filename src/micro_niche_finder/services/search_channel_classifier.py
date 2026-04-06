from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from micro_niche_finder.domain.schemas import OnlineGTMContext


CHANNEL_ORDER = ("community", "blog_content", "competitor", "marketplace_platform", "government", "noise")


@dataclass(frozen=True, slots=True)
class SearchResultDocument:
    title: str
    link: str | None = None
    snippet: str | None = None


class SearchChannelClassifier:
    def classify_documents(
        self,
        *,
        query: str,
        documents: list[SearchResultDocument],
        suggested_channels: list[str] | None = None,
    ) -> OnlineGTMContext:
        counts = {channel: 0 for channel in CHANNEL_ORDER}
        labels: list[str] = []

        for document in documents:
            channel = self._classify_document(document)
            counts[channel] += 1
            labels.append(channel)

        community_score = self._ratio(counts["community"], len(documents))
        content_score = self._ratio(counts["blog_content"] + counts["marketplace_platform"], len(documents))
        competitor_score = self._ratio(counts["competitor"], len(documents))
        signals = self._merge_signals(counts, suggested_channels or [])

        summary = (
            f"검색 결과 기준 채널 분포는 커뮤니티 {counts['community']}건, 콘텐츠 {counts['blog_content']}건, "
            f"경쟁사/도구 {counts['competitor']}건, 플랫폼 {counts['marketplace_platform']}건, 공공 {counts['government']}건이다."
        )

        return OnlineGTMContext(
            query=query,
            channel_signals=signals,
            channel_counts=counts,
            community_presence_score=round(community_score, 4),
            seo_discoverability_score=round(content_score, 4),
            competitor_presence_score=round(competitor_score, 4),
            summary=summary,
        )

    def score_from_context(self, context: OnlineGTMContext) -> float:
        total = sum(context.channel_counts.values())
        if total == 0:
            return 0.2

        community = self._ratio(context.channel_counts.get("community", 0), total)
        content = self._ratio(
            context.channel_counts.get("blog_content", 0) + context.channel_counts.get("marketplace_platform", 0),
            total,
        )
        competitor = self._ratio(context.channel_counts.get("competitor", 0), total)
        government = self._ratio(context.channel_counts.get("government", 0), total)
        noise = self._ratio(context.channel_counts.get("noise", 0), total)

        score = (community * 0.3) + (content * 0.3) + (competitor * 0.25) + (government * 0.05)
        score += min(0.1, len(context.channel_signals) * 0.025)
        score -= noise * 0.2
        return round(max(0.0, min(1.0, score)), 4)

    @staticmethod
    def _ratio(value: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return value / total

    def _classify_document(self, document: SearchResultDocument) -> str:
        text = " ".join(part for part in [document.title, document.snippet or ""] if part).lower()
        host = urlparse(document.link or "").netloc.lower()

        if self._matches(host, text, ("cafe.naver.com", "open.kakao.com", "cafe", "community", "forum", "카페", "커뮤니티")):
            return "community"
        if self._matches(
            host,
            text,
            ("blog.naver.com", "brunch.co.kr", "tistory.com", "velog.io", "medium.com", "blog", "가이드", "후기"),
        ):
            return "blog_content"
        if self._matches(
            host,
            text,
            (
                ".go.kr",
                "gov.kr",
                "kosis.kr",
                "data.go.kr",
                "정부",
                "공공",
                "지원사업",
                "정책",
            ),
        ):
            return "government"
        if self._matches(
            host,
            text,
            (
                "program",
                "software",
                "saas",
                "crm",
                "erp",
                "solution",
                "서비스",
                "솔루션",
                "프로그램",
                "툴",
                "자동화",
                "비교",
                "추천",
            ),
        ):
            return "competitor"
        if self._matches(
            host,
            text,
            (
                "smartstore.naver.com",
                "store.naver.com",
                "coupang.com",
                "11st.co.kr",
                "gmarket.co.kr",
                "auction.co.kr",
                "marketkurly",
                "platform",
                "스토어",
                "마켓",
            ),
        ):
            return "marketplace_platform"
        if self._matches(host, text, ("youtube.com", "instagram.com", "facebook.com", "news", "뉴스", "홍보")):
            return "noise"
        return "blog_content" if re.search(r"(운영|관리|가이드|방법|체크리스트)", text) else "noise"

    @staticmethod
    def _matches(host: str, text: str, markers: tuple[str, ...]) -> bool:
        haystack = f"{host} {text}"
        return any(marker in haystack for marker in markers)

    @staticmethod
    def _merge_signals(counts: dict[str, int], suggested_channels: list[str]) -> list[str]:
        detected: list[str] = []
        if counts["community"] > 0:
            detected.append("커뮤니티")
        if counts["blog_content"] > 0:
            detected.append("콘텐츠 SEO")
        if counts["competitor"] > 0:
            detected.append("도구 비교 키워드")
        if counts["marketplace_platform"] > 0:
            detected.append("플랫폼/마켓 채널")
        if counts["government"] > 0:
            detected.append("공공/협회 자료")

        for channel in suggested_channels:
            if channel not in detected:
                detected.append(channel)
        return detected[:5]
