from apps.worker.run_suspend_watchdog import WatchdogSnapshot, _exclude_watchdog_job, _summarize_blockers


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
        auto_suspend_disabled_sources=[],
    )

    blockers = _summarize_blockers(snapshot)

    assert blockers == []


def test_exclude_watchdog_job_filters_only_own_unit() -> None:
    lines = [
        "88887 repro-suspend-after-periodic.service start running",
        "88888 micro-niche-collector.service start waiting",
    ]

    assert _exclude_watchdog_job(lines) == ["88888 micro-niche-collector.service start waiting"]


def test_disabled_sources_are_reported_as_disabled() -> None:
    snapshot = WatchdogSnapshot(
        elapsed_seconds=60,
        system_jobs=[],
        user_jobs=[],
        active_system_units=[],
        active_user_units=[],
        inhibitors=[],
        auto_suspend_disabled_sources=["session:/run/user/1000/micro-niche-finder/auto-suspend.disabled"],
    )

    assert snapshot.auto_suspend_disabled_sources == ["session:/run/user/1000/micro-niche-finder/auto-suspend.disabled"]
