from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.services.gmail_service import GmailService


def test_gmail_recipient_list_parses_csv(monkeypatch) -> None:
    monkeypatch.setenv("GMAIL_TO_EMAILS", "a@example.com, b@example.com")
    get_settings.cache_clear()

    service = GmailService()

    assert service.recipient_list() == ["a@example.com", "b@example.com"]

    get_settings.cache_clear()
