from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .analyze import VariantSummary, round_metric


@dataclass(frozen=True)
class RegressionViolation:
    scenario: str
    variant: str
    metric: str
    baseline: float | None
    current: float | None
    delta_pct: float | None


METRICS = (
    ("startup_avg_ms", "startup_avg_ms"),
    ("startup_p95_ms", "startup_p95_ms"),
    ("image_mb_avg", "image_mb_avg"),
)


def _metric_value(summary: VariantSummary, field: str) -> float | None:
    if field == "startup_avg_ms":
        return summary.startup_avg_ms
    if field == "startup_p95_ms":
        return summary.startup_p95_ms
    if field == "image_mb_avg":
        return summary.image_mb_avg
    return None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _pct_change(current: float, baseline: float) -> float:
    return ((current - baseline) / baseline) * 100.0


def _optional_metric(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return round_metric(float(value))
    if isinstance(value, str):
        return round_metric(float(value))
    return None


def load_summaries(path: Path) -> list[VariantSummary]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("baseline report must be a JSON list")

    summaries: list[VariantSummary] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("baseline report must contain JSON objects")
        summaries.append(
            VariantSummary(
                scenario=str(item.get("scenario", "")),
                variant=str(item.get("variant", "")),
                runs=int(item.get("runs", 0)),
                build_avg_ms=_optional_metric(item.get("build_avg_ms")),
                build_stddev_ms=_optional_metric(item.get("build_stddev_ms")),
                build_ci95_low_ms=_optional_metric(item.get("build_ci95_low_ms")),
                build_ci95_high_ms=_optional_metric(item.get("build_ci95_high_ms")),
                startup_avg_ms=_optional_metric(item.get("startup_avg_ms")),
                startup_p95_ms=_optional_metric(item.get("startup_p95_ms")),
                startup_p99_ms=_optional_metric(item.get("startup_p99_ms")),
                startup_stddev_ms=_optional_metric(item.get("startup_stddev_ms")),
                startup_ci95_low_ms=_optional_metric(item.get("startup_ci95_low_ms")),
                startup_ci95_high_ms=_optional_metric(item.get("startup_ci95_high_ms")),
                gc_pause_ms_avg=_optional_metric(item.get("gc_pause_ms_avg")),
                alloc_mb_avg=_optional_metric(item.get("alloc_mb_avg")),
                startup_phase_boot_ms_avg=_optional_metric(item.get("startup_phase_boot_ms_avg")),
                startup_phase_context_ms_avg=_optional_metric(item.get("startup_phase_context_ms_avg")),
                startup_phase_web_server_ms_avg=_optional_metric(item.get("startup_phase_web_server_ms_avg")),
                startup_phase_total_ms_avg=_optional_metric(item.get("startup_phase_total_ms_avg")),
                image_mb_avg=_optional_metric(item.get("image_mb_avg")),
                success_rate_pct=round_metric(float(item.get("success_rate_pct", 0.0))) or 0.0,
                rss_mb_avg=_optional_metric(item.get("rss_mb_avg")),
                cpu_pct_avg=_optional_metric(item.get("cpu_pct_avg")),
                host=_optional_str(item.get("host")),
                docker_version=_optional_str(item.get("docker_version")),
                run_profile=_optional_str(item.get("run_profile")),
            )
        )
    return summaries


def detect_regressions(
    baseline: list[VariantSummary], current: list[VariantSummary], threshold_pct: float
) -> list[RegressionViolation]:
    baseline_map = {(summary.scenario, summary.variant): summary for summary in baseline}
    current_map = {(summary.scenario, summary.variant): summary for summary in current}
    violations: list[RegressionViolation] = []

    for key, baseline_summary in sorted(baseline_map.items()):
        current_summary = current_map.get(key)
        if current_summary is None:
            continue
        for metric_name, field in METRICS:
            baseline_value = _metric_value(baseline_summary, field)
            current_value = _metric_value(current_summary, field)
            if baseline_value is None and current_value is None:
                continue
            if baseline_value is None and current_value is not None:
                continue
            if baseline_value is not None and current_value is None:
                violations.append(
                    RegressionViolation(
                        scenario=baseline_summary.scenario,
                        variant=baseline_summary.variant,
                        metric=metric_name,
                        baseline=baseline_value,
                        current=None,
                        delta_pct=None,
                    )
                )
                continue
            assert baseline_value is not None
            assert current_value is not None
            delta_pct = _pct_change(current_value, baseline_value)
            if delta_pct > threshold_pct:
                violations.append(
                    RegressionViolation(
                        scenario=baseline_summary.scenario,
                        variant=baseline_summary.variant,
                        metric=metric_name,
                        baseline=baseline_value,
                        current=current_value,
                        delta_pct=delta_pct,
                    )
                )
    return violations


def format_regression_table(violations: list[RegressionViolation]) -> str:
    lines = [
        "| Scenario | Variant | Metric | Baseline | Current | Δ% |",
        "|---|---|---|---:|---:|---:|",
    ]
    for violation in violations:
        baseline = "-" if violation.baseline is None else f"{violation.baseline:.2f}"
        current = "-" if violation.current is None else f"{violation.current:.2f}"
        delta = "-" if violation.delta_pct is None else f"{violation.delta_pct:+.1f}%"
        lines.append(
            f"| {violation.scenario} | {violation.variant} | {violation.metric} | {baseline} | {current} | {delta} |"
        )
    return "\n".join(lines)


def format_regression_json(violations: list[RegressionViolation]) -> str:
    payload = [
        {
            "scenario": violation.scenario,
            "variant": violation.variant,
            "metric": violation.metric,
            "baseline": violation.baseline,
            "current": violation.current,
            "delta_pct": violation.delta_pct,
        }
        for violation in violations
    ]
    return json.dumps(payload, indent=2, sort_keys=True)
