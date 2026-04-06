from __future__ import annotations

from micro_niche_finder.bootstrap import get_container
from micro_niche_finder.config.database import SessionLocal


def main() -> None:
    container = get_container()
    with SessionLocal() as session:
        summary = container.daily_report_service.run(session=session)
    print(summary)


if __name__ == "__main__":
    main()
