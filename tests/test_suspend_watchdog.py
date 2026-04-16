from apps.worker.run_suspend_watchdog import WatchdogSnapshot, _summarize_blockers


def test_summarize_blockers_includes_all_active_sources() -> None:
    snapshot = WatchdogSnapshot(
        elapsed_seconds=120,
        system_jobs=["job-a", "job-b"],
        user_jobs=["user-job"],
        active_system_units=["micro-niche-auto-seeds.service"],
        active_user_units=["shorts-upload.service"],
        inhibitors=[],
    )

    blockers = _summarize_blockers(snapshot)

    assert blockers == [
        "system jobs queued: job-a, job-b",
        "user jobs queued: user-job",
        "active system units: micro-niche-auto-seeds.service",
        "active user units: shorts-upload.service",
    ]


def test_summarize_blockers_empty_when_idle() -> None:
    snapshot = WatchdogSnapshot(
        elapsed_seconds=300,
        system_jobs=[],
        user_jobs=[],
        active_system_units=[],
        active_user_units=[],
        inhibitors=[],
    )

    blockers = _summarize_blockers(snapshot)

    assert blockers == []
