from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from micro_niche_finder.bootstrap import get_container
from micro_niche_finder.config.database import Base, SessionLocal, engine
from micro_niche_finder.repos.candidate_repo import SeedCategoryRepository


def _build_telegram_message(summaries: list[dict[str, Any]]) -> str:
    lines = ["[Auto Seeds Report]"]
    for summary in summaries:
        lines.append(
            f"- {summary['seed_name']}: generated {summary['generated_candidates']}, "
            f"reported {summary['reported_candidates']}"
        )
        for report in summary.get("reports", [])[:3]:
            lines.append(
                f"  {report['recommended_priority']}. {report['title']} | buyer={report['buyer']} | "
                f"hook={report['landing_page_hook']}"
            )
    return "\n".join(lines)


def _build_raw_markdown(summaries: list[dict[str, Any]], generated_at: datetime) -> str:
    lines = [
        "# Auto Seeds Report",
        "",
        f"- generated_at: {generated_at.isoformat()}",
        f"- seed_count: {len(summaries)}",
        "",
    ]
    for summary in summaries:
        lines.extend(
            [
                f"## {summary['seed_name']}",
                "",
                f"- seed_id: {summary['seed_id']}",
                f"- created: {summary['created']}",
                f"- generated_candidates: {summary['generated_candidates']}",
                f"- reported_candidates: {summary['reported_candidates']}",
                "",
            ]
        )
        for report in summary.get("reports", []):
            lines.extend(
                [
                    f"### {report['recommended_priority']}. {report['title']}",
                    "",
                    f"- niche_name: {report['niche_name']}",
                    f"- persona: {report['persona']}",
                    f"- buyer: {report['buyer']}",
                    f"- landing_page_hook: {report['landing_page_hook']}",
                    f"- core_value_proposition: {report['core_value_proposition']}",
                    "",
                    "#### Validation Plan",
                    "",
                ]
            )
            lines.extend([f"- {item}" for item in report.get("validation_plan", [])])
            lines.extend(
                [
                    "",
                    "#### Kill Criteria",
                    "",
                ]
            )
            lines.extend([f"- {item}" for item in report.get("kill_criteria", [])])
            lines.extend(
                [
                    "",
                    "#### First 10 Leads",
                    "",
                ]
            )
            lines.extend([f"- {item}" for item in report.get("first_10_leads", [])])
            lines.extend(
                [
                    "",
                    "#### Price Test",
                    "",
                ]
            )
            lines.extend([f"- {item}" for item in report.get("price_test", [])])
            lines.extend(
                [
                    "",
                    "#### Raw JSON",
                    "",
                    "```json",
                    json.dumps(report, ensure_ascii=False, indent=2),
                    "```",
                    "",
                ]
            )
    return "\n".join(lines).strip() + "\n"


def _write_raw_report(raw_output_dir: str, summaries: list[dict[str, Any]], generated_at: datetime) -> str:
    target_dir = Path(raw_output_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"auto-seeds-report-{generated_at.strftime('%Y%m%d-%H%M%S')}.md"
    target_path = target_dir / filename
    target_path.write_text(_build_raw_markdown(summaries, generated_at), encoding="utf-8")
    return str(target_path)


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
    parser.add_argument("--send-telegram", action="store_true", help="Send the generated report summary to Telegram.")
    parser.add_argument(
        "--raw-output-dir",
        type=str,
        default=None,
        help="Optional directory where a markdown copy of the generated reports will be written.",
    )
    args = parser.parse_args()

    container = get_container()
    Base.metadata.create_all(bind=engine)
    discovery = container.llm_service.generate_seed_categories(seed_count=args.seed_count)
    summaries: list[dict[str, int | str | bool]] = []
    generated_at = datetime.now()

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
                    "reports": [report.model_dump(mode="json") for report in pipeline.reports],
                }
            )

    raw_output_path = _write_raw_report(args.raw_output_dir, summaries, generated_at) if args.raw_output_dir else None
    telegram_chunks = 0
    telegram_configured = container.telegram_service.is_configured()
    if args.send_telegram and summaries and telegram_configured:
        telegram_chunks = container.telegram_service.send_message(_build_telegram_message(summaries))

    print(
        {
            "seed_count": len(summaries),
            "raw_output_path": raw_output_path,
            "telegram_chunks": telegram_chunks,
            "telegram_configured": telegram_configured,
            "results": summaries,
        }
    )


if __name__ == "__main__":
    main()
