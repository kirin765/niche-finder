from __future__ import annotations

import argparse

from micro_niche_finder.bootstrap import get_container
from micro_niche_finder.config.database import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Run daily micro niche report delivery.")
    parser.add_argument(
        "--refresh-seeds",
        action="store_true",
        help="Regenerate seed suggestions before running the daily report.",
    )
    args = parser.parse_args()

    container = get_container()
    with SessionLocal() as session:
        summary = container.daily_report_service.run(session=session, refresh_seeds=args.refresh_seeds)
    print(summary)


if __name__ == "__main__":
    main()
