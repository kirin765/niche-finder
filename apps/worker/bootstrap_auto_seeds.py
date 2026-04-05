from __future__ import annotations

import argparse

from micro_niche_finder.bootstrap import get_container
from micro_niche_finder.config.database import SessionLocal
from micro_niche_finder.repos.candidate_repo import SeedCategoryRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate seed categories with LLM and bootstrap pipelines.")
    parser.add_argument("--seed-count", type=int, default=5, help="How many diverse seeds to generate.")
    parser.add_argument(
        "--candidate-count",
        type=int,
        default=5,
        help="How many problem candidates to generate per seed.",
    )
    parser.add_argument("--top-k", type=int, default=3, help="How many reports to create per seed.")
    args = parser.parse_args()

    container = get_container()
    discovery = container.llm_service.generate_seed_categories(seed_count=args.seed_count)
    summaries: list[dict[str, int | str | bool]] = []

    with SessionLocal() as session:
        repo = SeedCategoryRepository(session)
        for suggestion in discovery.seeds:
            seed = repo.get_by_name(suggestion.name)
            created = False
            if seed is None:
                seed = repo.create(name=suggestion.name, description=suggestion.description)
                created = True

            pipeline = container.pipeline_service.run(
                session=session,
                seed_category_id=seed.id,
                candidate_count=args.candidate_count,
                top_k=args.top_k,
            )
            session.commit()
            summaries.append(
                {
                    "seed_id": seed.id,
                    "seed_name": seed.name,
                    "created": created,
                    "generated_candidates": pipeline.generated_candidates,
                    "reported_candidates": pipeline.reported_candidates,
                }
            )

    print({"seed_count": len(summaries), "results": summaries})


if __name__ == "__main__":
    main()
