from __future__ import annotations

from micro_niche_finder.bootstrap import get_container


def main() -> None:
    container = get_container()
    summary = container.improvement_discovery_service.run()
    print(summary)


if __name__ == "__main__":
    main()
