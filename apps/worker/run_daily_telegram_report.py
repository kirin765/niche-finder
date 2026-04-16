from __future__ import annotations

import argparse
import sys

from apps.worker import bootstrap_auto_seeds


def main() -> None:
    parser = argparse.ArgumentParser(description="Compatibility daily Telegram report entrypoint.")
    parser.add_argument("--refresh-seeds", action="store_true", help="Accepted for compatibility.")
    parser.add_argument("--seed-count", type=int, default=2)
    parser.add_argument("--candidate-count", type=int, default=3)
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument("--raw-output-dir", default="llm-wiki/raw")
    args = parser.parse_args()

    sys.argv = [
        "bootstrap_auto_seeds",
        "--seed-count",
        str(args.seed_count),
        "--candidate-count",
        str(args.candidate_count),
        "--top-k",
        str(args.top_k),
        "--send-telegram",
        "--raw-output-dir",
        args.raw_output_dir,
    ]
    bootstrap_auto_seeds.main()


if __name__ == "__main__":
    main()
