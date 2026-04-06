from __future__ import annotations

import argparse
import json

from micro_niche_finder.config.database import SessionLocal
from micro_niche_finder.services.vertical_seed_migration_service import VerticalSeedMigrationService


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean up horizontal seed data and replace it with vertical-market seeds.")
    parser.add_argument("--dry-run", action="store_true", help="Show which seeds would change without writing.")
    args = parser.parse_args()

    service = VerticalSeedMigrationService()
    with SessionLocal() as session:
        summary = service.migrate(session, dry_run=args.dry_run)
        if not args.dry_run:
            session.commit()

    print(
        json.dumps(
            {
                "dry_run": args.dry_run,
                "removed_seed_names": summary.removed_seed_names,
                "inserted_seed_names": summary.inserted_seed_names,
                "kept_seed_names": summary.kept_seed_names,
                "deleted_candidate_count": summary.deleted_candidate_count,
                "deleted_query_group_count": summary.deleted_query_group_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
