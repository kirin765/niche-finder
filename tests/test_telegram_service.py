from micro_niche_finder.services.telegram_service import TelegramService


def test_telegram_message_splits_long_content() -> None:
    text = ("a" * 2000) + "\n\n" + ("b" * 2000)

    chunks = TelegramService._split_message(text, limit=2500)

    assert len(chunks) == 2
    assert all(len(chunk) <= 2500 for chunk in chunks)
