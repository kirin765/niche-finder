from __future__ import annotations

from micro_niche_finder.bootstrap import get_container
from micro_niche_finder.config.database import SessionLocal
from micro_niche_finder.repos.collection_repo import CollectionRepository
from micro_niche_finder.services.kosis_employee_service import KosisEmployeeService
from micro_niche_finder.services.naver_search_service import NaverSearchService
from micro_niche_finder.services.naver_shopping_insight_service import NaverShoppingInsightService


def main() -> None:
    container = get_container()
    with SessionLocal() as session:
        repo = CollectionRepository(session)
        kosis_options = (
            container.kosis_employee_service.industry_options()
            if container.kosis_employee_service.is_configured()
            else []
        )
        shopping_options = (
            container.naver_shopping_insight_service.category_options()
            if container.naver_shopping_insight_service.is_configured()
            else []
        )
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
            repo.upsert_schedule(
                query_group_id=query_group.id,
                source="google_custom_search",
                priority=max(1, container.collection_scheduler_service.settings.collector_default_priority - 20),
                cadence_minutes=container.collection_scheduler_service.settings.collector_schedule_cadence_minutes,
                collection_targets_json=[
                    target.model_dump(mode="json")
                    for target in container.collection_scheduler_service.google_default_targets(
                        len(query_group.queries_json)
                    )
                ],
                next_collect_at=container.collection_scheduler_service.default_next_collect_at(),
            )
            repo.upsert_schedule(
                query_group_id=query_group.id,
                source=NaverSearchService.SOURCE,
                priority=max(1, container.collection_scheduler_service.settings.collector_default_priority - 15),
                cadence_minutes=container.collection_scheduler_service.settings.collector_schedule_cadence_minutes,
                collection_targets_json=[
                    target.model_dump(mode="json")
                    for target in container.collection_scheduler_service.naver_search_default_targets(
                        len(query_group.queries_json)
                    )
                ],
                next_collect_at=container.collection_scheduler_service.default_next_collect_at(),
            )
            if kosis_options and query_group.problem_candidate is not None:
                selection = container.llm_service.select_kosis_industry(
                    canonical_name=query_group.canonical_name,
                    persona=query_group.problem_candidate.persona,
                    problem_summary=query_group.problem_candidate.pain,
                    query_group=query_group.queries_json,
                    options=kosis_options,
                )
                repo.upsert_schedule(
                    query_group_id=query_group.id,
                    source=KosisEmployeeService.SOURCE,
                    priority=max(1, container.collection_scheduler_service.settings.collector_default_priority - 10),
                    cadence_minutes=container.collection_scheduler_service.settings.kosis_employee_cadence_minutes,
                    collection_targets_json=[
                        target.model_dump(mode="json")
                        for target in container.collection_scheduler_service.kosis_default_targets(selection)
                    ],
                    next_collect_at=container.collection_scheduler_service.default_next_collect_at(),
                )
            if shopping_options and query_group.problem_candidate is not None:
                is_relevant = container.naver_shopping_insight_service.is_relevant_niche(
                    canonical_name=query_group.canonical_name,
                    persona=query_group.problem_candidate.persona,
                    problem_summary=query_group.problem_candidate.pain,
                    query_group=query_group.queries_json,
                )
                if is_relevant:
                    selection = container.llm_service.select_naver_shopping_category(
                        canonical_name=query_group.canonical_name,
                        persona=query_group.problem_candidate.persona,
                        problem_summary=query_group.problem_candidate.pain,
                        query_group=query_group.queries_json,
                        options=shopping_options,
                    )
                    repo.upsert_schedule(
                        query_group_id=query_group.id,
                        source=NaverShoppingInsightService.SOURCE,
                        priority=max(1, container.collection_scheduler_service.settings.collector_default_priority - 12),
                        cadence_minutes=container.collection_scheduler_service.settings.naver_shopping_insight_cadence_minutes,
                        collection_targets_json=[
                            target.model_dump(mode="json")
                            for target in container.collection_scheduler_service.naver_shopping_default_targets(selection)
                        ],
                        next_collect_at=container.collection_scheduler_service.default_next_collect_at(),
                    )
            count += 1
        for query_group in repo.list_query_groups_without_schedule_for_source(NaverSearchService.SOURCE):
            repo.upsert_schedule(
                query_group_id=query_group.id,
                source=NaverSearchService.SOURCE,
                priority=max(1, container.collection_scheduler_service.settings.collector_default_priority - 15),
                cadence_minutes=container.collection_scheduler_service.settings.collector_schedule_cadence_minutes,
                collection_targets_json=[
                    target.model_dump(mode="json")
                    for target in container.collection_scheduler_service.naver_search_default_targets(
                        len(query_group.queries_json)
                    )
                ],
                next_collect_at=container.collection_scheduler_service.default_next_collect_at(),
            )
        if kosis_options:
            for query_group in repo.list_query_groups_without_schedule_for_source(KosisEmployeeService.SOURCE):
                if query_group.problem_candidate is None:
                    continue
                selection = container.llm_service.select_kosis_industry(
                    canonical_name=query_group.canonical_name,
                    persona=query_group.problem_candidate.persona,
                    problem_summary=query_group.problem_candidate.pain,
                    query_group=query_group.queries_json,
                    options=kosis_options,
                )
                repo.upsert_schedule(
                    query_group_id=query_group.id,
                    source=KosisEmployeeService.SOURCE,
                    priority=max(1, container.collection_scheduler_service.settings.collector_default_priority - 10),
                    cadence_minutes=container.collection_scheduler_service.settings.kosis_employee_cadence_minutes,
                    collection_targets_json=[
                        target.model_dump(mode="json")
                        for target in container.collection_scheduler_service.kosis_default_targets(selection)
                    ],
                    next_collect_at=container.collection_scheduler_service.default_next_collect_at(),
                )
        if shopping_options:
            for query_group in repo.list_query_groups_without_schedule_for_source(NaverShoppingInsightService.SOURCE):
                if query_group.problem_candidate is None:
                    continue
                is_relevant = container.naver_shopping_insight_service.is_relevant_niche(
                    canonical_name=query_group.canonical_name,
                    persona=query_group.problem_candidate.persona,
                    problem_summary=query_group.problem_candidate.pain,
                    query_group=query_group.queries_json,
                )
                if not is_relevant:
                    continue
                selection = container.llm_service.select_naver_shopping_category(
                    canonical_name=query_group.canonical_name,
                    persona=query_group.problem_candidate.persona,
                    problem_summary=query_group.problem_candidate.pain,
                    query_group=query_group.queries_json,
                    options=shopping_options,
                )
                repo.upsert_schedule(
                    query_group_id=query_group.id,
                    source=NaverShoppingInsightService.SOURCE,
                    priority=max(1, container.collection_scheduler_service.settings.collector_default_priority - 12),
                    cadence_minutes=container.collection_scheduler_service.settings.naver_shopping_insight_cadence_minutes,
                    collection_targets_json=[
                        target.model_dump(mode="json")
                        for target in container.collection_scheduler_service.naver_shopping_default_targets(selection)
                    ],
                    next_collect_at=container.collection_scheduler_service.default_next_collect_at(),
                )
        session.commit()
    print(f"Bootstrapped schedules: {count}")


if __name__ == "__main__":
    main()
