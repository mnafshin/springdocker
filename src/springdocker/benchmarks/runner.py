from __future__ import annotations

import argparse
import csv
import socket
import subprocess
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from springdocker.benchmarks.generate import (
    EXPECTED_CSV_HEADER,
    NativeScenarioDefinition,
    StandardScenarioDefinition,
    default_scenarios,
)


@dataclass(frozen=True)
class RunnerOptions:
    profile: str
    runs_override: int | None
    skip_native: bool
    java_version: int


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    detail: str = ""


def _run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int = 300,
    capture_output: bool = False,
) -> CommandResult:
    try:
        if capture_output:
            completed = subprocess.run(
                args,
                cwd=cwd,
                check=False,
                text=True,
                timeout=timeout_seconds,
                capture_output=True,
            )
        else:
            completed = subprocess.run(
                args,
                cwd=cwd,
                check=False,
                text=True,
                timeout=timeout_seconds,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return CommandResult(
            returncode=completed.returncode,
            stdout=getattr(completed, "stdout", "") if capture_output else "",
            stderr=getattr(completed, "stderr", "") if capture_output else "",
        )
    except subprocess.TimeoutExpired:
        return CommandResult(returncode=124, detail=f"command timed out after {timeout_seconds}s")
    except OSError as exc:
        return CommandResult(returncode=127, detail=str(exc))


def parse_runner_args(profile: str, extra_args: list[str]) -> RunnerOptions:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runs", type=int, default=None)
    parser.add_argument("--skip-native", action="store_true")
    parser.add_argument("--java-version", type=int, default=17)
    parsed, unknown = parser.parse_known_args(extra_args)
    if unknown:
        raise ValueError(f"unknown runner arguments: {' '.join(unknown)}")
    return RunnerOptions(
        profile=profile,
        runs_override=parsed.runs,
        skip_native=parsed.skip_native,
        java_version=parsed.java_version,
    )


def _docker_version() -> str:
    result = _run_command(["docker", "--version"], capture_output=True, timeout_seconds=15)
    out = result.stdout.strip()
    if result.returncode == 0 and out:
        return out.replace(",", "").split()[-1]
    return "unknown"


def _wait_readiness(base_url: str, timeout_seconds: float = 40.0) -> int:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            with urllib.request.urlopen(base_url, timeout=2.0) as response:
                if response.status < 400:
                    return int((time.time() - start) * 1000)
        except (TimeoutError, urllib.error.URLError, ConnectionResetError, ConnectionError):
            pass
        time.sleep(0.25)
    return -1


def _stop_container(container_name: str) -> None:
    _run_command(["docker", "stop", container_name], timeout_seconds=30)


def _append_row(path: Path, row: list[str]) -> None:
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(row)


def _ensure_csv(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(EXPECTED_CSV_HEADER, encoding="utf-8")


def _tag_for(scenario_id: str, variant_name: str) -> str:
    return f"bench-{scenario_id}:{variant_name}".replace("_", "-")


def _runtime_flags(cpuset_cpus: str | None, memory_limit: str | None, normalized_runtime: bool) -> list[str]:
    flags: list[str] = []
    if cpuset_cpus:
        flags.extend(["--cpuset-cpus", cpuset_cpus])
    if memory_limit:
        flags.extend(["--memory", memory_limit])
    if normalized_runtime:
        flags.extend(["--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--tmpfs", "/tmp"])
    return flags


def _default_runs_for(profile: str, scenario_id: str) -> int:
    if scenario_id == "02-jep483-aot-cache":
        return 8 if profile == "quick" else 15
    return 3 if profile == "quick" else 10


def _run_standard_scenario(
    project_root: Path,
    scenario_dir: Path,
    runs: int,
    run_profile: str,
    cpuset_cpus: str | None,
    memory_limit: str | None,
    warmup_runs: int,
    port_seed: int,
    normalized_runtime: bool,
) -> None:
    raw_csv = scenario_dir / "results" / "raw.csv"
    _ensure_csv(raw_csv)
    host = socket.gethostname()
    docker_version = _docker_version()
    scenario = scenario_dir.name
    print(f"\n=== Scenario: {scenario} (runs={runs}, profile={run_profile}) ===")

    for index, variant_dir in enumerate(sorted((scenario_dir / "variants").glob("*"))):
        if not variant_dir.is_dir():
            continue
        dockerfile = variant_dir / "Dockerfile"
        if not dockerfile.exists():
            continue
        variant = variant_dir.name
        image_tag = _tag_for(scenario, variant)
        host_port = str(19081 + (port_seed * 50) + index)
        runtime_flags = _runtime_flags(cpuset_cpus=cpuset_cpus, memory_limit=memory_limit, normalized_runtime=normalized_runtime)
        print(f"-- variant: {variant}")

        for warmup_number in range(1, warmup_runs + 1):
            warmup_container = f"{image_tag.replace(':', '-')}-warmup-{warmup_number}"
            warmup_start_result = _run_command(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "--name",
                    warmup_container,
                    "-p",
                    f"{host_port}:8081",
                    *runtime_flags,
                    image_tag,
                ],
                timeout_seconds=60,
            )
            if warmup_start_result.returncode != 0:
                print(
                    f"warmup {warmup_number}: failed ({warmup_start_result.detail or warmup_start_result.stderr or 'docker run failed'})"
                )
                continue
            try:
                warmup_start = _wait_readiness("http://localhost:" + host_port + "/actuator/health/readiness")
                print(f"warmup {warmup_number}: startup={warmup_start}")
            finally:
                _stop_container(warmup_container)

        dockerfile_arg = dockerfile.relative_to(project_root).as_posix()
        for run_number in range(1, runs + 1):
            build_start = time.time()
            build = _run_command(
                ["docker", "build", "-q", "-f", dockerfile_arg, "-t", image_tag, "."],
                cwd=project_root,
                timeout_seconds=900,
                capture_output=True,
            )
            build_ms = int((time.time() - build_start) * 1000)
            if build.returncode != 0:
                _append_row(
                    raw_csv,
                    [
                        time.strftime("%Y-%m-%d"),
                        scenario,
                        variant,
                        str(run_number),
                        "-1",
                        "-1",
                        "-1",
                        "build_failed",
                        (build.stderr or build.stdout or build.detail or "docker build failed").strip(),
                        host,
                        docker_version,
                        run_profile,
                        "",
                        "",
                        "",
                        "",
                        "",
                    ],
                )
                print(f"run {run_number}: build failed")
                continue

            image_size_result = _run_command(
                ["docker", "image", "inspect", image_tag, "--format", "{{.Size}}"],
                capture_output=True,
                timeout_seconds=30,
            ).stdout.strip() or "-1"

            container_name = f"{image_tag.replace(':', '-')}-{run_number}"
            start_result = _run_command(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "--name",
                    container_name,
                    "-p",
                    f"{host_port}:8081",
                    *runtime_flags,
                    image_tag,
                ],
                timeout_seconds=60,
            )
            if start_result.returncode != 0:
                startup_ms = -1
                status = "run_failed"
                notes = start_result.detail or start_result.stderr or "docker run failed"
            else:
                try:
                    startup_ms = _wait_readiness("http://localhost:" + host_port + "/actuator/health/readiness")
                    status = "ok" if startup_ms >= 0 else "readiness_failed"
                    notes = "" if status == "ok" else "readiness endpoint not reachable"
                finally:
                    _stop_container(container_name)

            _append_row(
                raw_csv,
                [
                    time.strftime("%Y-%m-%d"),
                    scenario,
                    variant,
                    str(run_number),
                    str(build_ms),
                    image_size_result,
                    str(startup_ms),
                    status,
                    notes,
                    host,
                    docker_version,
                    run_profile,
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            )
            print(
                f"run {run_number}: build={build_ms}ms size={image_size_result} "
                f"startup={startup_ms} status={status}"
            )


def run_benchmarks(
    project_root: Path,
    build_tool: str,
    profile: str,
    extra_args: list[str],
    cpuset_cpus: str | None = None,
    memory_limit: str | None = None,
    warmup_runs: int = 0,
    max_workers: int = 1,
    normalized_runtime: bool = False,
) -> int:
    project_root = project_root.resolve()
    options = parse_runner_args(profile=profile, extra_args=extra_args)
    print(f"Using profile: {options.profile}")
    print(f"Project root: {project_root}")
    print(f"Build tool: {build_tool}")
    scenarios = default_scenarios(build_tool=build_tool, java_version=options.java_version)
    print(f"Scenarios loaded: {len(scenarios)}")

    work_items: list[tuple[int, Path, int]] = []
    for scenario_index, scenario in enumerate(scenarios):
        if isinstance(scenario, NativeScenarioDefinition):
            if options.skip_native:
                print(f"Skipping native scaffold scenario: {scenario.id}")
                continue
            print(
                f"Skipping native scaffold scenario in internal runner: {scenario.id} "
                "(not production-ready; see docs/native-aot.md)"
            )
            continue
        if not isinstance(scenario, StandardScenarioDefinition):  # pragma: no cover - defensive guard for future extensions
            raise TypeError(f"unsupported scenario definition: {type(scenario)}")
        scenario_dir = project_root / "benchmarks" / scenario.id
        if not (scenario_dir / "variants").exists():
            print(f"Skipping missing scenario directory: {scenario.id}")
            continue
        runs = options.runs_override or _default_runs_for(profile=options.profile, scenario_id=scenario.id)
        work_items.append((scenario_index, scenario_dir, runs))

    if max_workers <= 1 or len(work_items) <= 1:
        for scenario_index, scenario_dir, runs in work_items:
            _run_standard_scenario(
                project_root=project_root,
                scenario_dir=scenario_dir,
                runs=runs,
                run_profile=options.profile,
                cpuset_cpus=cpuset_cpus,
                memory_limit=memory_limit,
                warmup_runs=warmup_runs,
                port_seed=scenario_index,
                normalized_runtime=normalized_runtime,
            )
    else:
        print(f"Running standard scenarios concurrently (max_workers={max_workers})")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _run_standard_scenario,
                    project_root=project_root,
                    scenario_dir=scenario_dir,
                    runs=runs,
                    run_profile=options.profile,
                    cpuset_cpus=cpuset_cpus,
                    memory_limit=memory_limit,
                    warmup_runs=warmup_runs,
                    port_seed=scenario_index,
                    normalized_runtime=normalized_runtime,
                ): scenario_dir.name
                for scenario_index, scenario_dir, runs in work_items
            }
            for future in as_completed(futures):
                scenario_name = futures[future]
                try:
                    future.result()
                except Exception as exc:  # pragma: no cover - exercised via command-level integration flow
                    print(f"Scenario failed: {scenario_name}: {exc}")
                    return 1
    print("\nAll done. CSV results were updated.")
    return 0
