from __future__ import annotations

from micro_niche_finder.bootstrap import get_container
from micro_niche_finder.config.database import SessionLocal


def main() -> None:
    container = get_container()
    with SessionLocal() as session:
        summary = container.naver_shopping_insight_collector_service.run_once(session=session)
        session.commit()
    print(summary.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
