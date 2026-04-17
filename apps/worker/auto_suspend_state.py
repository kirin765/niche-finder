from __future__ import annotations

import os
from pathlib import Path


def _session_disable_file() -> Path:
    default_runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")
    default_path = Path(default_runtime_dir) / "micro-niche-finder" / "auto-suspend.disabled"
    return Path(os.environ.get("AUTO_SUSPEND_SESSION_DISABLE_FILE", str(default_path)))


def _global_disable_file() -> Path:
    return Path(os.environ.get("AUTO_SUSPEND_GLOBAL_DISABLE_FILE", "/etc/micro-niche-finder.auto-suspend.disabled"))


def disable_files() -> dict[str, Path]:
    return {
        "session": _session_disable_file(),
        "global": _global_disable_file(),
    }


def disabled_sources() -> list[str]:
    sources: list[str] = []
    for scope, path in disable_files().items():
        if path.exists():
            sources.append(f"{scope}:{path}")
    return sources


def is_disabled() -> bool:
    return bool(disabled_sources())


def set_disabled(scope: str) -> Path:
    path = disable_files()[scope]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return path


def clear_disabled(scope: str) -> Path:
    path = disable_files()[scope]
    if path.exists():
        path.unlink()
    return path
