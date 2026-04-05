from __future__ import annotations

import json

from micro_niche_finder.bootstrap import get_container
from micro_niche_finder.config.database import Base, SessionLocal, engine
from micro_niche_finder.repos.candidate_repo import SeedCategoryRepository


def main() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    container = get_container()
    with SessionLocal() as session:
        seed = SeedCategoryRepository(session).create(
            name="스마트스토어 운영",
            description="Ubuntu smoke test seed",
        )
        session.commit()

        result = container.pipeline_service.run(
            session=session,
            seed_category_id=seed.id,
            candidate_count=5,
            top_k=3,
        )
        session.commit()

    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
