from __future__ import annotations

from micro_niche_finder.bootstrap import get_container
from micro_niche_finder.config.database import SessionLocal
from micro_niche_finder.repos.candidate_repo import SeedCategoryRepository


def main() -> None:
    container = get_container()
    with SessionLocal() as session:
        repo = SeedCategoryRepository(session)
        seeds = repo.list_all()
        if not seeds:
            discovery = container.llm_service.generate_seed_categories(seed_count=5)
            for suggestion in discovery.seeds:
                repo.create(name=suggestion.name, description=suggestion.description)
            session.commit()
            seeds = repo.list_all()

        has_reports = False
        try:
            has_reports = len(repo.list_reports(limit=1)) > 0
        except Exception:
            has_reports = False

        if has_reports:
            print({"bootstrapped": False, "reason": "reports already exist"})
            return

        results = []
        for seed in seeds[:3]:
            pipeline = container.pipeline_service.run(
                session=session,
                seed_category_id=seed.id,
                candidate_count=3,
                top_k=1,
            )
            session.commit()
            results.append(
                {
                    "seed": seed.name,
                    "generated_candidates": pipeline.generated_candidates,
                    "reported_candidates": pipeline.reported_candidates,
                }
            )

        print({"bootstrapped": True, "results": results})


if __name__ == "__main__":
    main()
