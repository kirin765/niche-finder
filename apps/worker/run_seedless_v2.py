from __future__ import annotations

from micro_niche_finder.bootstrap import get_container
from micro_niche_finder.config.database import SessionLocal


def main() -> None:
    container = get_container()
    with SessionLocal() as session:
        summary = container.seedless_v2_service.run(session=session, send_telegram=True)
    print(summary)


if __name__ == "__main__":
    main()
