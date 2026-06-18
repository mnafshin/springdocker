#!/usr/bin/env python3
"""Print markdown tables from benchmark raw.csv files for presentation deck updates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from presentation_benchmark_lib import DEFAULT_PROJECT_ROOT, load_reports, render_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--output", type=Path, default=None, help="Write markdown to this file instead of stdout")
    parser.add_argument("--json", action="store_true", help="Include JSON blocks after each scenario table")
    args = parser.parse_args(argv)

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

    markdown = render_markdown(reports, include_json=args.json)
    if args.output is not None:
        args.output.write_text(markdown, encoding="utf-8")
        print(f"wrote summary: {args.output.resolve()}", file=sys.stderr)
    else:
        sys.stdout.write(markdown)

    return 0 if reports else 1


if __name__ == "__main__":
    raise SystemExit(main())
