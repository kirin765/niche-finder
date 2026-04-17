from __future__ import annotations

from apps.worker.auto_suspend_state import clear_disabled, disabled_sources, disable_files, set_disabled


def test_disable_and_enable_paths_can_be_toggled(tmp_path, monkeypatch) -> None:
    session_file = tmp_path / "session" / "auto-suspend.disabled"
    global_file = tmp_path / "global" / "auto-suspend.disabled"
    monkeypatch.setenv("AUTO_SUSPEND_SESSION_DISABLE_FILE", str(session_file))
    monkeypatch.setenv("AUTO_SUSPEND_GLOBAL_DISABLE_FILE", str(global_file))

    assert disabled_sources() == []

    set_disabled("session")
    assert session_file.exists()
    assert disabled_sources() == [f"session:{session_file}"]

    set_disabled("global")
    assert global_file.exists()
    assert disabled_sources() == [
        f"session:{session_file}",
        f"global:{global_file}",
    ]

    clear_disabled("session")
    clear_disabled("global")
    assert disabled_sources() == []


def test_disable_files_reflect_environment(tmp_path, monkeypatch) -> None:
    session_file = tmp_path / "session" / "auto-suspend.disabled"
    global_file = tmp_path / "global" / "auto-suspend.disabled"
    monkeypatch.setenv("AUTO_SUSPEND_SESSION_DISABLE_FILE", str(session_file))
    monkeypatch.setenv("AUTO_SUSPEND_GLOBAL_DISABLE_FILE", str(global_file))

    paths = disable_files()

    assert paths["session"] == session_file
    assert paths["global"] == global_file
