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

    get_settings.cache_clear()
