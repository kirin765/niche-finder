from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass

SYSTEM_BLOCKING_UNITS = (
    "micro-niche-auto-seeds.service",
    "japantravel-content-cycle.service",
)

USER_BLOCKING_UNITS = (
    "shorts-upload.service",
    "shorts-maker-history-upload.service",
    "shorts-maker-science-upload.service",
)


@dataclass(slots=True)
class WatchdogSnapshot:
    elapsed_seconds: int
    system_jobs: list[str]
    user_jobs: list[str]
    active_system_units: list[str]
    active_user_units: list[str]
    inhibitors: list[str]


def _run(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _list_jobs(command: list[str], *, env: dict[str, str] | None = None) -> list[str]:
    result = _run(command, env=env)
    if result.returncode != 0:
        return []
    return _nonempty_lines(result.stdout)


def _active_units(units: tuple[str, ...], *, env: dict[str, str] | None = None) -> list[str]:
    active: list[str] = []
    for unit in units:
        result = _run(["systemctl", "is-active", "--quiet", unit], env=env)
        if result.returncode == 0:
            active.append(unit)
    return active


def _collect_inhibitors() -> list[str]:
    result = _run(["systemd-inhibit", "--list", "--no-pager"])
    if result.returncode != 0:
        return []
    lines = _nonempty_lines(result.stdout)
    if len(lines) <= 1:
        return []
    return lines[1:]


def _summarize_blockers(snapshot: WatchdogSnapshot) -> list[str]:
    blockers: list[str] = []
    if snapshot.system_jobs:
        blockers.append(f"system jobs queued: {', '.join(snapshot.system_jobs)}")
    if snapshot.user_jobs:
        blockers.append(f"user jobs queued: {', '.join(snapshot.user_jobs)}")
    if snapshot.active_system_units:
        blockers.append(f"active system units: {', '.join(snapshot.active_system_units)}")
    if snapshot.active_user_units:
        blockers.append(f"active user units: {', '.join(snapshot.active_user_units)}")
    return blockers


def _snapshot(elapsed_seconds: int) -> WatchdogSnapshot:
    return WatchdogSnapshot(
        elapsed_seconds=elapsed_seconds,
        system_jobs=_list_jobs(["systemctl", "list-jobs", "--no-legend"]),
        user_jobs=_list_jobs(
            ["systemctl", "--user", "list-jobs", "--no-legend"],
            env={"XDG_RUNTIME_DIR": "/run/user/0"},
        ),
        active_system_units=_active_units(SYSTEM_BLOCKING_UNITS),
        active_user_units=_active_units(
            USER_BLOCKING_UNITS,
            env={"XDG_RUNTIME_DIR": "/run/user/0"},
        ),
        inhibitors=_collect_inhibitors(),
    )


def _print_snapshot(snapshot: WatchdogSnapshot) -> None:
    payload = {
        "elapsed_seconds": snapshot.elapsed_seconds,
        "system_jobs": snapshot.system_jobs,
        "user_jobs": snapshot.user_jobs,
        "active_system_units": snapshot.active_system_units,
        "active_user_units": snapshot.active_user_units,
        "inhibitors": snapshot.inhibitors,
        "blockers": _summarize_blockers(snapshot),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry suspend after periodic jobs until the system becomes idle.")
    parser.add_argument("--initial-delay-sec", type=int, default=120)
    parser.add_argument("--poll-interval-sec", type=int, default=60)
    parser.add_argument("--max-wait-sec", type=int, default=30 * 60)
    parser.add_argument(
        "--lock-file",
        default="/tmp/repro-suspend-after-periodic.lock",
        help="Prevent overlapping watchdog instances.",
    )
    args = parser.parse_args()

    lock_handle = open(args.lock_file, "w", encoding="utf-8")
    try:
        import fcntl

        try:
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(
                json.dumps(
                    {"status": "skipped", "reason": "another watchdog instance is already running"},
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return

        start = time.monotonic()
        time.sleep(max(0, args.initial_delay_sec))

        while True:
            elapsed_seconds = int(time.monotonic() - start)
            snapshot = _snapshot(elapsed_seconds=elapsed_seconds)
            _print_snapshot(snapshot)

            blockers = _summarize_blockers(snapshot)
            if not blockers:
                print(json.dumps({"status": "suspending", "elapsed_seconds": elapsed_seconds}, ensure_ascii=False))
                sys.stdout.flush()
                result = _run(["systemctl", "suspend"])
                if result.returncode != 0:
                    print(
                        json.dumps(
                            {
                                "status": "suspend_failed",
                                "returncode": result.returncode,
                                "stderr": result.stderr.strip(),
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
                return

            if elapsed_seconds >= args.max_wait_sec:
                print(
                    json.dumps(
                        {
                            "status": "gave_up_waiting",
                            "elapsed_seconds": elapsed_seconds,
                            "blockers": blockers,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                return

            time.sleep(max(1, args.poll_interval_sec))
    finally:
        try:
            lock_handle.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
