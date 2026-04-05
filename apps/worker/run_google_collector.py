from __future__ import annotations

import argparse

from micro_niche_finder.bootstrap import get_container
from micro_niche_finder.config.database import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one budgeted Google Custom Search collection cycle.")
    parser.add_argument("--max-calls", type=int, default=None, help="Optional hard cap for this run.")
    args = parser.parse_args()

    container = get_container()
    with SessionLocal() as session:
        summary = container.google_collector_service.run_once(session=session, max_calls=args.max_calls)
        session.commit()

    print(summary.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
