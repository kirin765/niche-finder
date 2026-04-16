from __future__ import annotations

import importlib
import sys

import pytest

from micro_niche_finder.config.settings import get_settings


def _reload_database_module():
    sys.modules.pop("micro_niche_finder.config.database", None)
    return importlib.import_module("micro_niche_finder.config.database")


def test_sqlite_database_url_is_rejected_outside_test_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="SQLite databases are only allowed when APP_ENV=test"):
        _reload_database_module()

    get_settings.cache_clear()


def test_sqlite_database_url_is_allowed_in_test_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    get_settings.cache_clear()

    module = _reload_database_module()

    assert module.engine.url.get_backend_name() == "sqlite"

    get_settings.cache_clear()
