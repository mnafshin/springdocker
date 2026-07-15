"""Load benchmark CSV summaries and refresh presentation HTML bindings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from springdocker.analyze import VariantSummary, format_json, format_table, summarize_csv

DEFAULT_PROJECT_ROOT = Path("samples/java-spring-docker")

SCENARIOS: tuple[tuple[str, str], ...] = (
    ("01-custom-jre-jlink", "Custom JRE via jlink + jdeps"),
    ("02-jep483-aot-cache", "JEP 483 AOT class-loading cache"),
    ("03-base-image-choice", "Runtime base image choice"),
    ("05-appcds", "AppCDS shared class archive"),
)

CROSS_CUTTING_ROWS: tuple[tuple[str, str, str], ...] = (
    ("Image size", "01-custom-jre-jlink", "temurin-jre-image"),
    ("Image size", "01-custom-jre-jlink", "without-jlink-runtime"),
    ("Image size", "01-custom-jre-jlink", "with-jlink-runtime"),
    ("Image size", "03-base-image-choice", "debian-slim"),
    ("Image size", "03-base-image-choice", "alpine"),
    ("Startup avg", "01-custom-jre-jlink", "without-jlink-runtime"),
    ("Startup avg", "05-appcds", "without-appcds"),
    ("Startup avg", "05-appcds", "with-appcds"),
    ("Startup avg", "02-jep483-aot-cache", "without-aot-cache"),
    ("Startup avg", "02-jep483-aot-cache", "with-aot-cache"),
)

BAR_GROUPS: dict[str, tuple[str, ...]] = {
    "scenario-01-image": (
        "01-custom-jre-jlink/temurin-jre-image/image_mb_avg",
        "01-custom-jre-jlink/without-jlink-runtime/image_mb_avg",
        "01-custom-jre-jlink/with-jlink-runtime/image_mb_avg",
    ),
    "cross-image-size": (
        "01-custom-jre-jlink/temurin-jre-image/image_mb_avg",
        "01-custom-jre-jlink/without-jlink-runtime/image_mb_avg",
        "01-custom-jre-jlink/with-jlink-runtime/image_mb_avg",
        "03-base-image-choice/distroless/image_mb_avg",
        "03-base-image-choice/alpine/image_mb_avg",
    ),
    "cross-startup": (
        "01-custom-jre-jlink/without-jlink-runtime/startup_avg_ms",
        "01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms",
        "05-appcds/with-appcds/startup_avg_ms",
        "02-jep483-aot-cache/with-aot-cache/startup_avg_ms",
    ),
    "features-image-size": (
        "01-custom-jre-jlink/temurin-jre-image/image_mb_avg",
        "01-custom-jre-jlink/without-jlink-runtime/image_mb_avg",
        "01-custom-jre-jlink/with-jlink-runtime/image_mb_avg",
        "03-base-image-choice/distroless/image_mb_avg",
        "03-base-image-choice/alpine/image_mb_avg",
    ),
    "features-cold-start": (
        "01-custom-jre-jlink/without-jlink-runtime/startup_avg_ms",
        "01-custom-jre-jlink/with-jlink-runtime/startup_avg_ms",
        "05-appcds/with-appcds/startup_avg_ms",
        "02-jep483-aot-cache/with-aot-cache/startup_avg_ms",
    ),
}

PRESENTATION_HTML_FILES: tuple[Path, ...] = (
    Path("docs/presentation/docker-steps-evidence.html"),
    Path("docs/presentation/springdocker-features.html"),
)

LOWER_IS_BETTER_METRICS: frozenset[str] = frozenset(
    {"image_mb_avg", "build_avg_ms", "startup_avg_ms", "startup_p95_ms"}
)
# Relative spread below this threshold is treated as noise — use warn, not risk.
SIGNIFICANT_RELATIVE_SPREAD = 0.10
AUTO_HIGHLIGHT_CLASSES: frozenset[str] = frozenset({"good", "risk", "warn"})
TABLE_RE = re.compile(r"<table\b.*?</table>", re.DOTALL | re.IGNORECASE)
TABLE_ROW_RE = re.compile(r"<tr\b.*?</tr>", re.DOTALL | re.IGNORECASE)
BENCHMARK_CELL_RE = re.compile(
    r"<td(?P<attrs>[^>]*)>"
    r"(?P<prefix>(?:(?!</td>).)*?)"
    r"(?P<inner><span[^>]*\sdata-benchmark=\"(?P<key>[^\"]+)\"[^>]*>[^<]*</span>)"
    r"(?P<suffix>(?:(?!</td>).)*?)"
    r"</td>",
    re.DOTALL | re.IGNORECASE,
)

BENCHMARK_SPAN_RE = re.compile(
    r'(<span[^>]*data-benchmark="(?P<key>[^"]+)"[^>]*>)(?P<content>[^<]*)(?P<close></span>)'
)
BENCHMARK_COMPUTED_RE = re.compile(
    r'(<span[^>]*data-benchmark-computed="(?P<key>[^"]+)"[^>]*>)(?P<content>[^<]*)(?P<close></span>)'
)
BENCHMARK_BAR_RE = re.compile(
    r'(<[^>]+\sdata-benchmark-bar="(?P<key>[^"]+)"[^>]*\sstyle=")(?P<style>[^"]*)(")'
)
BENCHMARK_STAMP_RE = re.compile(r"<!-- benchmark-updated: [^>]+ -->")


@dataclass(frozen=True)
class ScenarioReport:
    scenario_id: str
    title: str
    csv_path: Path
    summaries: tuple[VariantSummary, ...]


def benchmark_key(scenario_id: str, variant: str, metric: str) -> str:
    return f"{scenario_id}/{variant}/{metric}"


def fmt_ms(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:,.0f} ms"


def fmt_mb(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f} MB"


def metric_value(summary: VariantSummary, metric: str) -> float | None:
    return getattr(summary, metric)


def format_metric(summary: VariantSummary, metric: str) -> str:
    value = metric_value(summary, metric)
    if metric == "image_mb_avg":
        return fmt_mb(value)
    if metric.endswith("_ms") or metric.endswith("_ms_avg"):
        return fmt_ms(value)
    if value is None:
        return "-"
    return f"{value:.2f}"


def load_reports(project_root: Path) -> tuple[list[ScenarioReport], list[Path]]:
    reports: list[ScenarioReport] = []
    missing: list[Path] = []
    for scenario_id, title in SCENARIOS:
        csv_path = project_root / "benchmarks" / scenario_id / "results" / "raw.csv"
        if not csv_path.exists():
            missing.append(csv_path)
            continue
        reports.append(
            ScenarioReport(
                scenario_id=scenario_id,
                title=title,
                csv_path=csv_path,
                summaries=tuple(summarize_csv(csv_path)),
            )
        )
    return reports, missing


def build_formatted_values(reports: list[ScenarioReport]) -> tuple[dict[str, str], dict[str, float], dict[str, str]]:
    formatted: dict[str, str] = {}
    numeric: dict[str, float] = {}
    computed: dict[str, str] = {}

    metrics = ("image_mb_avg", "build_avg_ms", "startup_avg_ms", "startup_p95_ms")
    for report in reports:
        for summary in report.summaries:
            for metric in metrics:
                key = benchmark_key(report.scenario_id, summary.variant, metric)
                value = metric_value(summary, metric)
                if value is None:
                    continue
                formatted[key] = format_metric(summary, metric)
                numeric[key] = value

    return formatted, numeric, computed


def metric_from_benchmark_key(key: str) -> str:
    return key.rsplit("/", 1)[-1]


def relative_spread(best: float, worst: float) -> float:
    if best <= 0:
        return 0.0
    return (worst - best) / best


def set_td_highlight_class(attrs: str, highlight: str | None) -> str:
    class_match = re.search(r'\sclass="([^"]*)"', attrs)
    if class_match:
        classes = [item for item in class_match.group(1).split() if item not in AUTO_HIGHLIGHT_CLASSES]
        if highlight:
            classes.append(highlight)
        attrs = re.sub(r'\sclass="[^"]*"', f' class="{" ".join(classes)}"' if classes else "", attrs, count=1)
        return attrs
    if highlight:
        return f'{attrs} class="{highlight}"'
    return attrs


def highlight_class_for_column(key: str, column_keys: tuple[str, ...], numeric: dict[str, float]) -> str | None:
    metric = metric_from_benchmark_key(key)
    if metric not in LOWER_IS_BETTER_METRICS:
        return None

    values = [(item, numeric[item]) for item in column_keys if item in numeric]
    if len(values) < 2:
        return None

    measured = numeric.get(key)
    if measured is None:
        return None

    numbers = [value for _, value in values]
    best = min(numbers)
    worst = max(numbers)
    if best == worst:
        return None

    significant = relative_spread(best, worst) >= SIGNIFICANT_RELATIVE_SPREAD

    if measured == best:
        return "good"
    if measured == worst:
        return "risk" if significant else "warn"
    return "warn" if not significant else None


def apply_table_cell_highlights(html: str, numeric: dict[str, float]) -> str:
    def replace_table(match: re.Match[str]) -> str:
        table_html = match.group(0)
        if "data-benchmark=" not in table_html:
            return table_html

        rows = TABLE_ROW_RE.findall(table_html)
        if not rows:
            return table_html

        parsed_rows: list[list[tuple[str, str, str, str, str, str]]] = []
        max_columns = 0
        for row_html in rows:
            cells = [
                (
                    cell_match.group("attrs"),
                    cell_match.group("prefix"),
                    cell_match.group("inner"),
                    cell_match.group("suffix"),
                    cell_match.group("key"),
                    cell_match.group(0),
                )
                for cell_match in BENCHMARK_CELL_RE.finditer(row_html)
            ]
            parsed_rows.append(cells)
            max_columns = max(max_columns, len(cells))

        if max_columns == 0:
            return table_html

        columns: list[list[str]] = [[] for _ in range(max_columns)]
        for cells in parsed_rows:
            for index, (_, _, _, _, key, _) in enumerate(cells):
                columns[index].append(key)

        updated_rows: list[str] = []
        for row_html, cells in zip(rows, parsed_rows, strict=False):
            updated_row = row_html
            for index, (attrs, prefix, inner, suffix, key, original_cell) in enumerate(cells):
                highlight = highlight_class_for_column(key, tuple(columns[index]), numeric)
                new_attrs = set_td_highlight_class(attrs, highlight)
                replacement = f"<td{new_attrs}>{prefix}{inner}{suffix}</td>"
                updated_row = updated_row.replace(original_cell, replacement, 1)
            updated_rows.append(updated_row)

        updated_table = table_html
        for original_row, updated_row in zip(rows, updated_rows, strict=False):
            updated_table = updated_table.replace(original_row, updated_row, 1)
        return updated_table

    return TABLE_RE.sub(replace_table, html)


def update_bar_width(style: str, width_pct: int) -> str:
    if re.search(r"width\s*:", style):
        return re.sub(r"width\s*:\s*[^;]+", f"width:{width_pct}%", style)
    return f"{style};width:{width_pct}%" if style else f"width:{width_pct}%"


def apply_benchmark_data(html: str, formatted: dict[str, str], numeric: dict[str, float], computed: dict[str, str]) -> str:
    def replace_span(match: re.Match[str]) -> str:
        key = match.group("key")
        if key not in formatted:
            return match.group(0)
        return f"{match.group(1)}{formatted[key]}{match.group('close')}"

    def replace_computed(match: re.Match[str]) -> str:
        key = match.group("key")
        if key not in computed:
            return match.group(0)
        content = match.group("content")
        suffix = ""
        if "×" in content:
            suffix = content[content.index("×") + 1 :]
        return f"{match.group(1)}{computed[key]}{suffix}{match.group('close')}"

    updated = BENCHMARK_SPAN_RE.sub(replace_span, html)
    updated = BENCHMARK_COMPUTED_RE.sub(replace_computed, updated)

    for _group_name, keys in BAR_GROUPS.items():
        present = {key: numeric[key] for key in keys if key in numeric}
        if len(present) < 2:
            continue
        max_value = max(present.values())

        def replace_bar(match: re.Match[str], present: dict[str, float] = present, max_value: float = max_value) -> str:
            key = match.group("key")
            if key not in present or max_value <= 0:
                return match.group(0)
            width_pct = max(1, round(present[key] / max_value * 100))
            style = update_bar_width(match.group("style"), width_pct)
            return f'{match.group(1)}{style}{match.group(4)}'

        updated = BENCHMARK_BAR_RE.sub(replace_bar, updated)

    return apply_table_cell_highlights(updated, numeric)


def touch_benchmark_stamp(html: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp_line = f"<!-- benchmark-updated: {stamp} -->"
    if BENCHMARK_STAMP_RE.search(html):
        return BENCHMARK_STAMP_RE.sub(stamp_line, html, count=1)
    return html.replace("<body>", f"<body>\n  {stamp_line}", 1)


def apply_benchmark_bindings(html: str, formatted: dict[str, str], numeric: dict[str, float], computed: dict[str, str]) -> str:
    updated = apply_benchmark_data(html, formatted, numeric, computed)
    if updated != html:
        updated = touch_benchmark_stamp(updated)
    return updated


def update_presentation_html(path: Path, formatted: dict[str, str], numeric: dict[str, float], computed: dict[str, str]) -> bool:
    if not path.exists():
        return False
    original = path.read_text(encoding="utf-8")
    if "data-benchmark=" not in original and "data-benchmark-bar=" not in original:
        return False
    updated = apply_benchmark_bindings(original, formatted, numeric, computed)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
    return True


def render_markdown(reports: list[ScenarioReport], *, include_json: bool) -> str:
    lines: list[str] = [
        "# Benchmark presentation summary",
        "",
        "Generated by `python scripts/update_presentation_benchmarks.py`.",
        "",
    ]

    if not reports:
        lines.append("_No scenario CSV files found._")
        return "\n".join(lines) + "\n"

    lines.extend(["## Cross-cutting values", "", "| Goal | Scenario | Variant | Image | Build | Startup |", "|---|---|---|---:|---:|---:|"])
    for goal, scenario_id, variant in CROSS_CUTTING_ROWS:
        summary = next(
            (item for item in reports if item.scenario_id == scenario_id),
            None,
        )
        row = next((item for item in (summary.summaries if summary else ()) if item.variant == variant), None)
        if row is None:
            lines.append(f"| {goal} | `{scenario_id}` | `{variant}` | - | - | - |")
            continue
        lines.append(
            f"| {goal} | `{scenario_id}` | `{variant}` | {fmt_mb(row.image_mb_avg)} | "
            f"{fmt_ms(row.build_avg_ms)} | {fmt_ms(row.startup_avg_ms)} |"
        )
    lines.append("")

    for report in reports:
        lines.extend([f"## {report.scenario_id} — {report.title}", "", f"Source: `{report.csv_path}`", ""])
        lines.append(format_table(list(report.summaries)))
        lines.append("")
        if include_json:
            lines.extend(["```json", format_json(list(report.summaries)), "```", ""])

    return "\n".join(lines).rstrip() + "\n"
