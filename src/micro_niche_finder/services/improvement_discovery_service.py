from __future__ import annotations

from dataclasses import dataclass

from micro_niche_finder.domain.schemas import GoogleSearchRequest
from micro_niche_finder.services.google_search_service import GoogleSearchService
from micro_niche_finder.services.telegram_service import TelegramService


@dataclass(slots=True)
class ImprovementDiscoverySummary:
    topics_checked: int
    messages_sent: int
    highlights: list[str]


class ImprovementDiscoveryService:
    SEARCH_TOPICS = [
        "micro saas validation framework niche idea evaluation",
        "manual first saas concierge mvp examples",
        "seo friendly micro saas keyword opportunities",
        "vertical saas distribution channels community acquisition",
        "low arpu niche saas monetization examples",
        "service assisted saas pricing model examples",
        "micro niche software business viability signals",
        "bootstrap saas go to market long tail seo",
    ]

    def __init__(self, google_search_service: GoogleSearchService, telegram_service: TelegramService) -> None:
        self.google_search_service = google_search_service
        self.telegram_service = telegram_service

    def run(self) -> ImprovementDiscoverySummary:
        highlights: list[str] = []
        for topic in self.SEARCH_TOPICS:
            response = self.google_search_service.fetch(GoogleSearchRequest(q=topic, num=5, gl="us", hl="en"))
            for item in response.items[:3]:
                title = (item.title or "").strip()
                snippet = (item.snippet or "").strip()
                link = (item.link or "").strip()
                if not title:
                    continue
                highlights.append(self._format_highlight(topic=topic, title=title, snippet=snippet, link=link))

        highlights = self._dedupe(highlights)[:8]
        message = self._build_message(highlights)
        sent = self.telegram_service.send_message(message) if self.telegram_service.is_configured() else 0
        return ImprovementDiscoverySummary(
            topics_checked=len(self.SEARCH_TOPICS),
            messages_sent=sent,
            highlights=highlights,
        )

    def _build_message(self, highlights: list[str]) -> str:
        header = (
            "[Niche Finder Improvement Discovery]\n"
            "- Mode: 6-hour periodic idea search\n"
            "- Purpose: 사업성 판단 / GTM / SEO / manual-first 개선 아이디어 탐색"
        )
        if not highlights:
            return header + "\n\n새로 요약할 개선 아이디어를 찾지 못했습니다."
        body = "\n\n".join(f"{idx + 1}. {item}" for idx, item in enumerate(highlights))
        footer = (
            "\n\n메모: 이 잡은 자동 개선이 아니라, 프로젝트 개선 아이디어를 주기적으로 찾아 텔레그램으로 전달합니다."
        )
        return header + "\n\n" + body + footer

    def _format_highlight(self, *, topic: str, title: str, snippet: str, link: str) -> str:
        compact_topic = topic.replace("micro saas", "micro-SaaS")
        snippet = " ".join(snippet.split())[:220] if snippet else "요약 없음"
        link_text = f"\n{link}" if link else ""
        return f"[{compact_topic}] {title}\n{snippet}{link_text}"

    def _dedupe(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            key = item.lower().split("\n", 1)[0]
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result
