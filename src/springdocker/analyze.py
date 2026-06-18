from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

REQUIRED_COLUMNS = {
    "scenario",
    "variant",
    "build_ms",
    "startup_ms",
    "image_bytes",
    "status",
}
OPTIONAL_COLUMNS = {"rss_bytes", "cpu_pct", "host", "docker_version", "run_profile"}
OPTIONAL_COLUMNS |= {
    "gc_pause_ms",
    "alloc_mb",
    "startup_phase_boot_ms",
    "startup_phase_context_ms",
    "startup_phase_web_server_ms",
}

# Keep JSON baselines stable across Python versions (statistics.quantiles differs on 3.10 vs 3.11+).
METRIC_FLOAT_DECIMALS = 6


def round_metric(value: float | None, places: int = METRIC_FLOAT_DECIMALS) -> float | None:
    if value is None:
        return None
    return float(round(value, places))


@dataclass(frozen=True)
class VariantSummary:
    scenario: str
    variant: str
    runs: int
    build_avg_ms: float | None
    startup_avg_ms: float | None
    startup_p95_ms: float | None
    image_mb_avg: float | None
    success_rate_pct: float
    build_stddev_ms: float | None = None
    build_ci95_low_ms: float | None = None
    build_ci95_high_ms: float | None = None
    startup_p99_ms: float | None = None
    startup_stddev_ms: float | None = None
    startup_ci95_low_ms: float | None = None
    startup_ci95_high_ms: float | None = None
    gc_pause_ms_avg: float | None = None
    alloc_mb_avg: float | None = None
    startup_phase_boot_ms_avg: float | None = None
    startup_phase_context_ms_avg: float | None = None
    startup_phase_web_server_ms_avg: float | None = None
    startup_phase_total_ms_avg: float | None = None
    rss_mb_avg: float | None = None
    cpu_pct_avg: float | None = None
    host: str | None = None
    docker_version: str | None = None
    run_profile: str | None = None


def _to_int_or_none(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _p95(values: list[int]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round_metric(float(values[0]))
    return round_metric(statistics.quantiles(values, n=20)[18])


def _p99(values: list[int]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round_metric(float(values[0]))
    return round_metric(statistics.quantiles(values, n=100)[98])


def _stddev(values: list[int]) -> float | None:
    if len(values) < 2:
        return None
    return round_metric(statistics.stdev(values))


def _ci95(values: list[int]) -> tuple[float | None, float | None]:
    if len(values) < 2:
        return None, None
    mean = statistics.mean(values)
    stddev = statistics.stdev(values)
    margin = 1.96 * (stddev / math.sqrt(len(values)))
    return round_metric(mean - margin), round_metric(mean + margin)


def _mean_float(values: list[float]) -> float | None:
    return round_metric(statistics.mean(values)) if values else None


def _mean_int(values: list[int]) -> float | None:
    return round_metric(statistics.mean(values)) if values else None


def summarize_csv(path: Path, scenario: str | None = None, variant: str | None = None) -> list[VariantSummary]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - fieldnames)
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

        rows: list[dict[str, str]] = list(reader)

    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        sc = row.get("scenario", "")
        vr = row.get("variant", "")
        if scenario and sc != scenario:
            continue
        if variant and vr != variant:
            continue
        groups.setdefault((sc, vr), []).append(row)

    summaries: list[VariantSummary] = []
    for (sc, vr), items in sorted(groups.items()):
        build = [v for i in items if (v := _to_int_or_none(i.get("build_ms", ""))) is not None and v >= 0]
        startup = [v for i in items if (v := _to_int_or_none(i.get("startup_ms", ""))) is not None and v >= 0]
        image = [v for i in items if (v := _to_int_or_none(i.get("image_bytes", ""))) is not None and v >= 0]
        rss: list[int] = []
        for item in items:
            rss_value = _to_int_or_none(item.get("rss_bytes", ""))
            if rss_value is not None and rss_value >= 0:
                rss.append(rss_value)

        cpu: list[float] = []
        for item in items:
            cpu_value = _to_float_or_none(item.get("cpu_pct", ""))
            if cpu_value is not None and cpu_value >= 0.0:
                cpu.append(cpu_value)

        gc_pause: list[float] = []
        alloc: list[float] = []
        phase_boot: list[float] = []
        phase_context: list[float] = []
        phase_web_server: list[float] = []
        for item in items:
            if (value := _to_float_or_none(item.get("gc_pause_ms", ""))) is not None and value >= 0.0:
                gc_pause.append(value)
            if (value := _to_float_or_none(item.get("alloc_mb", ""))) is not None and value >= 0.0:
                alloc.append(value)
            if (value := _to_float_or_none(item.get("startup_phase_boot_ms", ""))) is not None and value >= 0.0:
                phase_boot.append(value)
            if (value := _to_float_or_none(item.get("startup_phase_context_ms", ""))) is not None and value >= 0.0:
                phase_context.append(value)
            if (value := _to_float_or_none(item.get("startup_phase_web_server_ms", ""))) is not None and value >= 0.0:
                phase_web_server.append(value)

        ok = sum(1 for i in items if i.get("status") == "ok")
        total = len(items)
        first = items[0] if items else {}
        build_ci95_low, build_ci95_high = _ci95(build)
        startup_ci95_low, startup_ci95_high = _ci95(startup)

        summaries.append(
            VariantSummary(
                scenario=sc,
                variant=vr,
                runs=total,
                build_avg_ms=_mean_int(build),
                build_stddev_ms=_stddev(build),
                build_ci95_low_ms=build_ci95_low,
                build_ci95_high_ms=build_ci95_high,
                startup_avg_ms=_mean_int(startup),
                startup_p95_ms=_p95(startup),
                startup_p99_ms=_p99(startup),
                startup_stddev_ms=_stddev(startup),
                startup_ci95_low_ms=startup_ci95_low,
                startup_ci95_high_ms=startup_ci95_high,
                gc_pause_ms_avg=_mean_float(gc_pause),
                alloc_mb_avg=_mean_float(alloc),
                startup_phase_boot_ms_avg=_mean_float(phase_boot),
                startup_phase_context_ms_avg=_mean_float(phase_context),
                startup_phase_web_server_ms_avg=_mean_float(phase_web_server),
                startup_phase_total_ms_avg=round_metric(
                    (_mean_float(phase_boot) or 0.0)
                    + (_mean_float(phase_context) or 0.0)
                    + (_mean_float(phase_web_server) or 0.0)
                )
                if any([phase_boot, phase_context, phase_web_server])
                else None,
                image_mb_avg=round_metric(statistics.mean(image) / (1024 * 1024)) if image else None,
                rss_mb_avg=round_metric(statistics.mean(rss) / (1024 * 1024)) if rss else None,
                cpu_pct_avg=_mean_float(cpu),
                success_rate_pct=(round_metric((ok / total) * 100.0) or 0.0) if total else 0.0,
                host=first.get("host") or None,
                docker_version=first.get("docker_version") or None,
                run_profile=first.get("run_profile") or None,
            )
        )

    return summaries


def format_table(summaries: list[VariantSummary]) -> str:
    lines = [
        "| Scenario | Variant | Runs | Build avg (ms) | Build stddev (ms) | Build CI95 (ms) | Startup avg (ms) | Startup stddev (ms) | Startup p95 (ms) | Startup p99 (ms) | Startup CI95 (ms) | GC pause avg (ms) | Alloc avg (MB) | Boot avg (ms) | Context avg (ms) | Web server avg (ms) | Startup phase total (ms) | Image MB avg | RSS MB avg | CPU avg (%) | Success rate | Host | Docker | Profile |",
        "|---|---|---:|---:|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]

    for s in summaries:
        build_avg = f"{s.build_avg_ms:.1f}" if s.build_avg_ms is not None else "-"
        build_stddev = f"{s.build_stddev_ms:.1f}" if s.build_stddev_ms is not None else "-"
        build_ci95 = (
            f"{s.build_ci95_low_ms:.1f}..{s.build_ci95_high_ms:.1f}"
            if s.build_ci95_low_ms is not None and s.build_ci95_high_ms is not None
            else "-"
        )
        startup_avg = f"{s.startup_avg_ms:.1f}" if s.startup_avg_ms is not None else "-"
        startup_stddev = f"{s.startup_stddev_ms:.1f}" if s.startup_stddev_ms is not None else "-"
        startup_p95 = f"{s.startup_p95_ms:.1f}" if s.startup_p95_ms is not None else "-"
        startup_p99 = f"{s.startup_p99_ms:.1f}" if s.startup_p99_ms is not None else "-"
        startup_ci95 = (
            f"{s.startup_ci95_low_ms:.1f}..{s.startup_ci95_high_ms:.1f}"
            if s.startup_ci95_low_ms is not None and s.startup_ci95_high_ms is not None
            else "-"
        )
        gc_pause = f"{s.gc_pause_ms_avg:.1f}" if s.gc_pause_ms_avg is not None else "-"
        alloc = f"{s.alloc_mb_avg:.2f}" if s.alloc_mb_avg is not None else "-"
        boot = f"{s.startup_phase_boot_ms_avg:.1f}" if s.startup_phase_boot_ms_avg is not None else "-"
        context = f"{s.startup_phase_context_ms_avg:.1f}" if s.startup_phase_context_ms_avg is not None else "-"
        web_server = f"{s.startup_phase_web_server_ms_avg:.1f}" if s.startup_phase_web_server_ms_avg is not None else "-"
        phase_total = (
            f"{s.startup_phase_total_ms_avg:.1f}" if s.startup_phase_total_ms_avg is not None else "-"
        )
        image_mb = f"{s.image_mb_avg:.2f}" if s.image_mb_avg is not None else "-"
        rss_mb = f"{s.rss_mb_avg:.2f}" if s.rss_mb_avg is not None else "-"
        cpu_pct = f"{s.cpu_pct_avg:.1f}" if s.cpu_pct_avg is not None else "-"
        lines.append(
            f"| {s.scenario} | {s.variant} | {s.runs} | {build_avg} | {build_stddev} | {build_ci95} | "
            f"{startup_avg} | {startup_stddev} | {startup_p95} | {startup_p99} | {startup_ci95} | "
            f"{gc_pause} | {alloc} | {boot} | {context} | {web_server} | {phase_total} | "
            f"{image_mb} | {rss_mb} | {cpu_pct} | {s.success_rate_pct:.1f}% | "
            f"{s.host or '-'} | {s.docker_version or '-'} | {s.run_profile or '-'} |"
        )

    return "\n".join(lines)


def format_json(summaries: list[VariantSummary]) -> str:
    payload = [
        {
            "scenario": s.scenario,
            "variant": s.variant,
            "runs": s.runs,
            "build_avg_ms": s.build_avg_ms,
            "build_stddev_ms": s.build_stddev_ms,
            "build_ci95_low_ms": s.build_ci95_low_ms,
            "build_ci95_high_ms": s.build_ci95_high_ms,
            "startup_avg_ms": s.startup_avg_ms,
            "startup_p95_ms": s.startup_p95_ms,
            "startup_p99_ms": s.startup_p99_ms,
            "startup_stddev_ms": s.startup_stddev_ms,
            "startup_ci95_low_ms": s.startup_ci95_low_ms,
            "startup_ci95_high_ms": s.startup_ci95_high_ms,
            "gc_pause_ms_avg": s.gc_pause_ms_avg,
            "alloc_mb_avg": s.alloc_mb_avg,
            "startup_phase_boot_ms_avg": s.startup_phase_boot_ms_avg,
            "startup_phase_context_ms_avg": s.startup_phase_context_ms_avg,
            "startup_phase_web_server_ms_avg": s.startup_phase_web_server_ms_avg,
            "startup_phase_total_ms_avg": s.startup_phase_total_ms_avg,
            "image_mb_avg": s.image_mb_avg,
            "rss_mb_avg": s.rss_mb_avg,
            "cpu_pct_avg": s.cpu_pct_avg,
            "success_rate_pct": s.success_rate_pct,
            "host": s.host,
            "docker_version": s.docker_version,
            "run_profile": s.run_profile,
        }
        for s in summaries
    ]
    return json.dumps(payload, indent=2, sort_keys=True)
