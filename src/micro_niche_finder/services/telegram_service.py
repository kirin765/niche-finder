from __future__ import annotations

from collections.abc import Iterable

import httpx

from micro_niche_finder.config.settings import get_settings


class TelegramService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return bool(self.settings.telegram_bot_token and self.settings.telegram_chat_id)

    def send_message(self, text: str) -> int:
        if not self.is_configured():
            raise RuntimeError("Telegram service is not configured")
        chunks = self._split_message(text)
        total = len(chunks)
        sent = 0
        with httpx.Client(timeout=20.0) as client:
            for index, chunk in enumerate(chunks, start=1):
                numbered = chunk if total == 1 else f"({index}/{total})\n{chunk}"
                response = client.post(
                    f"{self.settings.telegram_base_url}/bot{self.settings.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": self.settings.telegram_chat_id,
                        "text": numbered,
                        "disable_web_page_preview": True,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if not payload.get("ok", False):
                    raise RuntimeError(f"Telegram API error: {payload}")
                sent += 1
        return sent

    @staticmethod
    def _split_message(text: str, limit: int = 3500) -> list[str]:
        if len(text) <= limit:
            return [text]
        chunks: list[str] = []
        current = ""
        for paragraph in TelegramService._paragraphs(text):
            candidate = paragraph if not current else f"{current}\n\n{paragraph}"
            if len(candidate) <= limit:
                current = candidate
                continue
            if current:
                chunks.append(current)
            if len(paragraph) <= limit:
                current = paragraph
                continue
            lines = TelegramService._split_hard(paragraph, limit)
            chunks.extend(lines[:-1])
            current = lines[-1]
        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def _paragraphs(text: str) -> Iterable[str]:
        return [paragraph for paragraph in text.split("\n\n") if paragraph]

    @staticmethod
    def _split_hard(text: str, limit: int) -> list[str]:
        return [text[index : index + limit] for index in range(0, len(text), limit)]
