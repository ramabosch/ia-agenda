from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.acceptance_runner import render_markdown_report, run_acceptance_suite


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run conversational acceptance scenarios against Agenda AI. "
            "Use the full suite by default, or filter by category/tag/severity, "
            "or run the predefined smoke critical suite."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "artifacts" / "acceptance"),
        help="Directory where JSON and Markdown reports will be written.",
    )
    parser.add_argument("--category", action="append", default=[], help="Filter by category. Repeatable.")
    parser.add_argument("--severity", action="append", default=[], help="Filter by severity. Repeatable.")
    parser.add_argument("--tag", action="append", default=[], help="Filter by tag. Repeatable.")
    parser.add_argument(
        "--smoke-critical",
        action="store_true",
        help="Run the predefined smoke critical suite (tag: smoke_critical).",
    )
    args = parser.parse_args()

    tag_filters = list(args.tag)
    if args.smoke_critical and "smoke_critical" not in tag_filters:
        tag_filters.append("smoke_critical")

    report = run_acceptance_suite(
        output_dir=args.output_dir,
        category_filters=args.category,
        severity_filters=args.severity,
        tag_filters=tag_filters,
    )
    summary = report.get("summary", {})

    print(
        json.dumps(
            {
                "scenario_count": report.get("scenario_count"),
                "pass": summary.get("pass", 0),
                "fail": summary.get("fail", 0),
                "partial": summary.get("partial", 0),
                "gate_status": summary.get("gate_status"),
                "by_category": summary.get("by_category", {}),
                "by_severity": summary.get("by_severity", {}),
                "failing_scenarios": summary.get("failing_scenarios", []),
                "selected_filters": report.get("selected_filters", {}),
                "artifacts": report.get("artifacts", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print()
    print(render_markdown_report(report))

    return 1 if summary.get("fail", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
