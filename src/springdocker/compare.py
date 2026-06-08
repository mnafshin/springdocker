from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

from .analyze import VariantSummary


@dataclass(frozen=True)
class VariantDelta:
    scenario: str
    variant: str
    baseline_variant: str
    is_baseline: bool
    build_delta_ms: float | None
    build_delta_pct: float | None
    startup_delta_ms: float | None
    startup_delta_pct: float | None
    image_delta_mb: float | None
    image_delta_pct: float | None


def _pct_delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None or baseline == 0:
        return None
    return ((value - baseline) / baseline) * 100.0


def _abs_delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return value - baseline


def compare_summaries(baseline_variant: str, summaries: list[VariantSummary]) -> list[VariantDelta]:
    by_scenario: dict[str, list[VariantSummary]] = {}
    for summary in summaries:
        by_scenario.setdefault(summary.scenario, []).append(summary)

    deltas: list[VariantDelta] = []
    for scenario, items in sorted(by_scenario.items()):
        baseline = next((item for item in items if item.variant == baseline_variant), None)
        if baseline is None:
            available = ", ".join(sorted(item.variant for item in items)) or "-"
            raise ValueError(f"baseline variant '{baseline_variant}' not found for scenario '{scenario}'; available: {available}")

        deltas.append(
            VariantDelta(
                scenario=scenario,
                variant=baseline.variant,
                baseline_variant=baseline_variant,
                is_baseline=True,
                build_delta_ms=0.0,
                build_delta_pct=0.0,
                startup_delta_ms=0.0,
                startup_delta_pct=0.0,
                image_delta_mb=0.0,
                image_delta_pct=0.0,
            )
        )

        for item in sorted(items, key=lambda summary: summary.variant):
            if item.variant == baseline_variant:
                continue
            deltas.append(
                VariantDelta(
                    scenario=scenario,
                    variant=item.variant,
                    baseline_variant=baseline_variant,
                    is_baseline=False,
                    build_delta_ms=_abs_delta(item.build_avg_ms, baseline.build_avg_ms),
                    build_delta_pct=_pct_delta(item.build_avg_ms, baseline.build_avg_ms),
                    startup_delta_ms=_abs_delta(item.startup_avg_ms, baseline.startup_avg_ms),
                    startup_delta_pct=_pct_delta(item.startup_avg_ms, baseline.startup_avg_ms),
                    image_delta_mb=_abs_delta(item.image_mb_avg, baseline.image_mb_avg),
                    image_delta_pct=_pct_delta(item.image_mb_avg, baseline.image_mb_avg),
                )
            )

    return deltas


def _render_delta(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "-"
    if suffix == "%":
        return f"{value:+.1f}%"
    if suffix == "mb":
        return f"{value:+.2f}"
    if suffix == "ms":
        return f"{value:+.1f}"
    return f"{value:+.1f}"


def format_delta_table(deltas: Iterable[VariantDelta]) -> str:
    lines = [
        "| Scenario | Variant | Baseline | Build Δms | Build Δ% | Startup Δms | Startup Δ% | Image ΔMB | Image Δ% |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for delta in deltas:
        lines.append(
            "| "
            + " | ".join(
                [
                    delta.scenario,
                    delta.variant,
                    delta.baseline_variant,
                    _render_delta(delta.build_delta_ms, "ms"),
                    _render_delta(delta.build_delta_pct, "%"),
                    _render_delta(delta.startup_delta_ms, "ms"),
                    _render_delta(delta.startup_delta_pct, "%"),
                    _render_delta(delta.image_delta_mb, "mb"),
                    _render_delta(delta.image_delta_pct, "%"),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def format_delta_json(deltas: Iterable[VariantDelta]) -> str:
    payload = [
        {
            "scenario": delta.scenario,
            "variant": delta.variant,
            "baseline_variant": delta.baseline_variant,
            "is_baseline": delta.is_baseline,
            "build_delta_ms": delta.build_delta_ms,
            "build_delta_pct": delta.build_delta_pct,
            "startup_delta_ms": delta.startup_delta_ms,
            "startup_delta_pct": delta.startup_delta_pct,
            "image_delta_mb": delta.image_delta_mb,
            "image_delta_pct": delta.image_delta_pct,
        }
        for delta in deltas
    ]
    return json.dumps(payload, indent=2, sort_keys=True)
