#!/usr/bin/env python3
"""Group missing coverage.py lines by their surrounding Python object."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CodeNode:
    node_type: str
    qualified_name: str
    start_line: int
    end_line: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze a coverage.py JSON report and group missing Python lines "
            "by class or function."
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--coverage-json", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-targets", type=int, default=200)
    parser.add_argument("--preview-lines", type=int, default=80)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    coverage_path = args.coverage_json.resolve()

    if not repo_root.is_dir():
        raise SystemExit(f"Repository root does not exist: {repo_root}")
    if args.max_targets < 1:
        raise SystemExit("--max-targets must be positive")
    if args.preview_lines < 1:
        raise SystemExit("--preview-lines must be positive")

    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    report = analyze_coverage(
        repo_root=repo_root,
        coverage=coverage,
        max_targets=args.max_targets,
        preview_lines=args.preview_lines,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"

    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote coverage analysis to {args.output}")

    return 0


def analyze_coverage(
    *,
    repo_root: Path,
    coverage: dict[str, Any],
    max_targets: int,
    preview_lines: int,
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []

    for reported_path, payload in coverage.get("files", {}).items():
        resolved = resolve_repo_file(repo_root, reported_path)
        if resolved is None or resolved.suffix != ".py":
            continue

        relative = resolved.relative_to(repo_root).as_posix()
        summary = normalize_summary(payload.get("summary", {}))
        missing_lines = sorted(set(payload.get("missing_lines", [])))
        executed_lines = sorted(set(payload.get("executed_lines", [])))
        files.append(
            {
                "path": relative,
                "summary": summary,
                "executed_lines": executed_lines,
                "missing_lines": missing_lines,
            }
        )

        if should_skip_target_file(Path(relative)) or not missing_lines:
            continue

        source = resolved.read_text(encoding="utf-8", errors="replace")
        source_lines = source.splitlines()
        nodes = collect_code_nodes(source)
        grouped: dict[CodeNode, list[int]] = {}

        for line_number in missing_lines:
            node = best_node(nodes, line_number)
            if node is None:
                node = CodeNode(
                    node_type="module",
                    qualified_name="<module>",
                    start_line=1,
                    end_line=max(len(source_lines), 1),
                )
            grouped.setdefault(node, []).append(line_number)

        file_percent = float(summary.get("percent_covered", 0.0))
        for node, node_lines in grouped.items():
            targets.append(
                {
                    "source_file": relative,
                    "node_type": node.node_type,
                    "qualified_name": node.qualified_name,
                    "start_line": node.start_line,
                    "end_line": node.end_line,
                    "file_percent_covered": round(file_percent, 2),
                    "missing_lines": node_lines,
                    "missing_line_ranges": line_ranges(node_lines),
                    "missing_line_count": len(node_lines),
                    "source_preview": source_preview(
                        source_lines,
                        node,
                        node_lines,
                        preview_lines,
                    ),
                }
            )

    files.sort(key=lambda item: item["path"])
    targets.sort(
        key=lambda item: (
            item["file_percent_covered"],
            -item["missing_line_count"],
            item["source_file"],
            item["start_line"],
        )
    )

    return {
        "format": "karabo-pytest-coverage-analysis-v1",
        "totals": normalize_summary(coverage.get("totals", {})),
        "files": files,
        "targets": targets[:max_targets],
        "target_count": min(len(targets), max_targets),
        "targets_available": len(targets),
        "selection_note": (
            "Targets are coverage candidates, not test recommendations. "
            "Select only behavior with a stable observable effect."
        ),
    }


def normalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "covered_lines",
        "num_statements",
        "percent_covered",
        "percent_covered_display",
        "missing_lines",
        "excluded_lines",
        "num_branches",
        "num_partial_branches",
        "covered_branches",
        "missing_branches",
    )
    return {key: summary[key] for key in keys if key in summary}


def resolve_repo_file(repo_root: Path, reported_path: str) -> Path | None:
    path = Path(reported_path)
    resolved = path.resolve() if path.is_absolute() else (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return None
    if not resolved.is_file():
        return None
    return resolved


def should_skip_target_file(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    return (
        "test" in lowered_parts
        or "tests" in lowered_parts
        or name in {"__init__.py", "conftest.py", "_version.py"}
        or name.startswith("test_")
        or name.endswith("_test.py")
    )


def collect_code_nodes(source: str) -> list[CodeNode]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    nodes: list[CodeNode] = []

    def visit(node: ast.AST, prefix: tuple[str, ...], in_class: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                qualified = ".".join((*prefix, child.name))
                nodes.append(
                    CodeNode(
                        node_type="class",
                        qualified_name=qualified,
                        start_line=child.lineno,
                        end_line=end_line(child),
                    )
                )
                visit(child, (*prefix, child.name), True)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = ".".join((*prefix, child.name))
                kind = "method" if in_class else "function"
                if isinstance(child, ast.AsyncFunctionDef):
                    kind = f"async_{kind}"
                nodes.append(
                    CodeNode(
                        node_type=kind,
                        qualified_name=qualified,
                        start_line=child.lineno,
                        end_line=end_line(child),
                    )
                )
            else:
                visit(child, prefix, in_class)

    visit(tree, (), False)
    return nodes


def end_line(node: ast.AST) -> int:
    return int(getattr(node, "end_lineno", getattr(node, "lineno", 1)))


def best_node(nodes: list[CodeNode], line_number: int) -> CodeNode | None:
    candidates = [
        node
        for node in nodes
        if node.start_line <= line_number <= node.end_line
    ]
    if not candidates:
        return None

    def priority(node: CodeNode) -> tuple[int, int]:
        is_class = 1 if node.node_type == "class" else 0
        return is_class, node.end_line - node.start_line

    return min(candidates, key=priority)


def line_ranges(lines: list[int]) -> str:
    if not lines:
        return ""

    result: list[str] = []
    start = previous = lines[0]
    for line_number in lines[1:]:
        if line_number == previous + 1:
            previous = line_number
            continue
        result.append(format_range(start, previous))
        start = previous = line_number
    result.append(format_range(start, previous))
    return ", ".join(result)


def format_range(start: int, end: int) -> str:
    return str(start) if start == end else f"{start}-{end}"


def source_preview(
    source_lines: list[str],
    node: CodeNode,
    missing_lines: list[int],
    max_lines: int,
) -> str:
    if not source_lines:
        return ""

    start = max(node.start_line, 1)
    end = min(node.end_line, len(source_lines))
    if end - start + 1 > max_lines:
        center = missing_lines[0]
        before = max_lines // 2
        start = max(node.start_line, center - before, 1)
        end = min(start + max_lines - 1, node.end_line, len(source_lines))
        start = max(node.start_line, end - max_lines + 1, 1)

    missing = set(missing_lines)
    return "\n".join(
        f"{'>>' if number in missing else '  '} {number:4d}: "
        f"{source_lines[number - 1]}"
        for number in range(start, end + 1)
    )


if __name__ == "__main__":
    raise SystemExit(main())
