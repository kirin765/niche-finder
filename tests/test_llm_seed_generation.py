from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.services.llm_service import OpenAIResearchService


def test_llm_seed_generation_mock_returns_seed_list(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()

    service = OpenAIResearchService()
    discovery = service.generate_seed_categories(seed_count=3)

    assert len(discovery.seeds) == 3
    assert all(item.name for item in discovery.seeds)
    assert all(item.description for item in discovery.seeds)
    assert all(item.rationale for item in discovery.seeds)
    forbidden = ("crm", "erp", "groupware", "hr", "accounting", "project management", "marketing")
    assert all(not any(token in item.name.lower() for token in forbidden) for item in discovery.seeds)

    get_settings.cache_clear()


def test_llm_seed_generation_mock_excludes_existing_seed_names(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()

    service = OpenAIResearchService()
    discovery = service.generate_seed_categories(
        seed_count=3,
        existing_seed_names=["스마트스토어 운영", "학원 운영"],
    )

    names = [item.name for item in discovery.seeds]
    assert "스마트스토어 운영" not in names
    assert "학원 운영" not in names
    assert len(names) == 3

    get_settings.cache_clear()
