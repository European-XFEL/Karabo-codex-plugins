#!/usr/bin/env python3
"""Compare two coverage.py JSON reports without changing either repository."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare before and after coverage.py JSON reports."
    )
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-regression", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    before = load_json(args.before)
    after = load_json(args.after)
    comparison = compare_reports(before, after)
    rendered = json.dumps(comparison, indent=2, sort_keys=True) + "\n"

    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote coverage comparison to {args.output}")

    if args.fail_on_regression and comparison["status"] == "regressed":
        return 1
    return 0


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.resolve().read_text(encoding="utf-8"))


def compare_reports(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    before_totals = totals(before)
    after_totals = totals(after)
    percent_delta = rounded_delta(
        after_totals.get("percent_covered", 0.0),
        before_totals.get("percent_covered", 0.0),
    )
    covered_delta = int(after_totals.get("covered_lines", 0)) - int(
        before_totals.get("covered_lines", 0)
    )
    statement_delta = int(after_totals.get("num_statements", 0)) - int(
        before_totals.get("num_statements", 0)
    )

    if percent_delta < 0 or covered_delta < 0:
        status = "regressed"
    elif percent_delta > 0 or covered_delta > 0:
        status = "improved"
    else:
        status = "unchanged"

    before_files = before.get("files", {})
    after_files = after.get("files", {})
    file_changes: list[dict[str, Any]] = []

    for path in sorted(set(before_files) | set(after_files)):
        old = before_files.get(path)
        new = after_files.get(path)
        if old is None:
            file_changes.append({"path": path, "status": "added_to_report"})
            continue
        if new is None:
            file_changes.append({"path": path, "status": "removed_from_report"})
            continue

        old_missing = set(old.get("missing_lines", []))
        new_missing = set(new.get("missing_lines", []))
        old_summary = old.get("summary", {})
        new_summary = new.get("summary", {})
        newly_covered = sorted(old_missing - new_missing)
        newly_missing = sorted(new_missing - old_missing)
        file_percent_delta = rounded_delta(
            new_summary.get("percent_covered", 0.0),
            old_summary.get("percent_covered", 0.0),
        )

        if newly_covered or newly_missing or file_percent_delta:
            file_changes.append(
                {
                    "path": path,
                    "status": "changed",
                    "before_percent": rounded(
                        old_summary.get("percent_covered", 0.0)
                    ),
                    "after_percent": rounded(
                        new_summary.get("percent_covered", 0.0)
                    ),
                    "percent_delta": file_percent_delta,
                    "newly_covered_lines": newly_covered,
                    "newly_missing_lines": newly_missing,
                }
            )

    return {
        "format": "karabo-pytest-coverage-comparison-v1",
        "status": status,
        "totals": {
            "before_percent": rounded(
                before_totals.get("percent_covered", 0.0)
            ),
            "after_percent": rounded(after_totals.get("percent_covered", 0.0)),
            "percent_delta": percent_delta,
            "covered_lines_delta": covered_delta,
            "statement_delta": statement_delta,
        },
        "file_changes": file_changes,
    }


def totals(report: dict[str, Any]) -> dict[str, Any]:
    value = report.get("totals")
    if not isinstance(value, dict):
        raise ValueError("Coverage report has no 'totals' object")
    return value


def rounded(value: Any) -> float:
    return round(float(value), 2)


def rounded_delta(after: Any, before: Any) -> float:
    return round(float(after) - float(before), 2)


if __name__ == "__main__":
    raise SystemExit(main())
