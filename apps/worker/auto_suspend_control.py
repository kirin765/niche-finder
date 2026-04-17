from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.worker.auto_suspend_state import clear_disabled, disabled_sources, disable_files, set_disabled


def _scope_paths(scope: str) -> list[tuple[str, Path]]:
    if scope == "session":
        return [("session", disable_files()["session"])]
    if scope == "global":
        return [("global", disable_files()["global"])]
    if scope == "both":
        return list(disable_files().items())
    raise ValueError(f"Unknown scope: {scope}")


def _toggle(scope: str, enabled: bool) -> list[str]:
    paths: list[str] = []
    for scope_name, path in _scope_paths(scope):
        if enabled:
            clear_disabled(scope_name)
        else:
            set_disabled(scope_name)
        paths.append(str(path))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Toggle auto suspend for the periodic watchdog.")
    parser.add_argument("action", choices=("status", "enable", "disable", "toggle"))
    parser.add_argument(
        "--scope",
        choices=("session", "global", "both"),
        default="session",
        help="Which disable marker to change. Defaults to the current session.",
    )
    args = parser.parse_args()

    if args.action == "status":
        print(
            json.dumps(
                {
                    "disabled": bool(disabled_sources()),
                    "disabled_sources": disabled_sources(),
                    "paths": {scope: str(path) for scope, path in disable_files().items()},
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return

    if args.action == "disable":
        paths = _toggle(args.scope, enabled=False)
        print(json.dumps({"action": "disable", "paths": paths}, ensure_ascii=False, sort_keys=True))
        return

    if args.action == "toggle":
        if disabled_sources():
            paths = _toggle(args.scope, enabled=True)
            print(json.dumps({"action": "enable", "paths": paths}, ensure_ascii=False, sort_keys=True))
            return
        paths = _toggle(args.scope, enabled=False)
        print(json.dumps({"action": "disable", "paths": paths}, ensure_ascii=False, sort_keys=True))
        return

    paths = _toggle(args.scope, enabled=True)
    print(json.dumps({"action": "enable", "paths": paths}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
