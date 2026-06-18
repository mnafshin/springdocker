#!/usr/bin/env python3
"""Refresh presentation HTML decks and markdown summary from benchmark raw.csv files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from presentation_benchmark_lib import (
    DEFAULT_PROJECT_ROOT,
    PRESENTATION_HTML_FILES,
    apply_benchmark_bindings,
    apply_benchmark_data,
    build_formatted_values,
    load_reports,
    render_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument(
        "--presentation-root",
        type=Path,
        default=Path("docs/presentation"),
        help="Directory containing Reveal.js decks to update",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("docs/presentation/benchmark-summary.md"),
        help="Write markdown summary to this path (use '-' to skip)",
    )
    parser.add_argument("--json", action="store_true", help="Include JSON blocks in markdown summary")
    parser.add_argument("--check", action="store_true", help="Exit non-zero if benchmark data in HTML would change")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    project_root = args.project_root.resolve()
    if not project_root.is_dir():
        print(f"missing project root: {project_root}", file=sys.stderr)
        return 1

    reports, missing = load_reports(project_root)
    if missing:
        print("Missing benchmark CSV files (run `springdocker benchmark run` first):", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        print("", file=sys.stderr)

    if not reports:
        return 1

    formatted, numeric, computed = build_formatted_values(reports)
    html_targets = [repo_root / path for path in PRESENTATION_HTML_FILES]
    if args.presentation_root != Path("docs/presentation"):
        html_targets = sorted(args.presentation_root.glob("*.html"))

    changed_files: list[Path] = []
    skipped_files: list[Path] = []
    for path in html_targets:
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        if "data-benchmark=" not in original and "data-benchmark-bar=" not in original:
            skipped_files.append(path)
            continue
        updated = apply_benchmark_data(original, formatted, numeric, computed)
        if updated != original:
            changed_files.append(path)
            if not args.check:
                path.write_text(apply_benchmark_bindings(original, formatted, numeric, computed), encoding="utf-8")

    if args.summary_output != Path("-"):
        summary_path = args.summary_output if args.summary_output.is_absolute() else repo_root / args.summary_output
        summary_path.write_text(render_markdown(reports, include_json=args.json), encoding="utf-8")
        print(f"wrote summary: {summary_path.resolve()}", file=sys.stderr)

    for path in changed_files:
        action = "would update" if args.check else "updated"
        print(f"{action}: {path.resolve()}", file=sys.stderr)
    for path in skipped_files:
        print(f"skipped (no benchmark bindings): {path.resolve()}", file=sys.stderr)

    if args.check and changed_files:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
