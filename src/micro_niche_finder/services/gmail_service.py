from __future__ import annotations

import smtplib
from email.message import EmailMessage

from micro_niche_finder.config.settings import get_settings


class GmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return bool(
            self.settings.gmail_username
            and self.settings.gmail_app_password
            and self.settings.gmail_from_email
            and self.recipient_list()
        )

    def recipient_list(self) -> list[str]:
        if not self.settings.gmail_to_emails:
            return []
        return [item.strip() for item in self.settings.gmail_to_emails.split(",") if item.strip()]

    def send_email(self, *, subject: str, body: str) -> int:
        if not self.is_configured():
            raise RuntimeError("Gmail service is not configured")

        recipients = self.recipient_list()
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.settings.gmail_from_email
        message["To"] = ", ".join(recipients)
        message.set_content(body)

        with smtplib.SMTP_SSL(self.settings.gmail_smtp_host, self.settings.gmail_smtp_port, timeout=30) as smtp:
            smtp.login(self.settings.gmail_username, self.settings.gmail_app_password)
            smtp.send_message(message)
        return len(recipients)
