from __future__ import annotations

from micro_niche_finder.bootstrap import get_container
from micro_niche_finder.config.database import SessionLocal
from micro_niche_finder.repos.collection_repo import CollectionRepository


def main() -> None:
    container = get_container()
    with SessionLocal() as session:
        repo = CollectionRepository(session)
        query_groups = repo.list_query_groups_without_schedule()
        count = 0
        for query_group in query_groups:
            repo.upsert_schedule(
                query_group_id=query_group.id,
                source="naver_datalab",
                priority=container.collection_scheduler_service.settings.collector_default_priority,
                cadence_minutes=container.collection_scheduler_service.settings.collector_schedule_cadence_minutes,
                collection_targets_json=[
                    target.model_dump(mode="json") for target in container.collection_scheduler_service.default_targets()
                ],
                next_collect_at=container.collection_scheduler_service.default_next_collect_at(),
            )
            count += 1
        session.commit()
    print(f"Bootstrapped schedules: {count}")


if __name__ == "__main__":
    main()
