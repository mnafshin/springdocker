from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast
from xml.sax.saxutils import escape

from ..plugins import iter_verifier_entry_points

VerifyStatus = Literal["passed", "failed", "skipped"]


@dataclass(frozen=True)
class VerifyResult:
    name: str
    status: VerifyStatus
    detail: str
    duration_ms: int


@dataclass(frozen=True)
class VerifyOutcome:
    results: tuple[VerifyResult, ...]

    @property
    def failed(self) -> bool:
        return any(item.status == "failed" for item in self.results)


@dataclass(frozen=True)
class VerifyContext:
    project_root: Path
    dockerfile_path: Path
    image: str | None
    smoke_url: str | None
    check_config_drift: bool = False
    build_tool: str | None = None
    trivy_scan_project_root: bool = False


def _trivy_scan_targets(context: VerifyContext) -> tuple[tuple[Path, ...], str]:
    if context.trivy_scan_project_root:
        return (context.project_root.resolve(),), "project root"
    dockerfile = context.dockerfile_path.resolve()
    dockerfile_dir = dockerfile.parent
    targets: list[Path] = [dockerfile]
    if dockerfile_dir not in targets:
        targets.append(dockerfile_dir)
    return tuple(targets), "dockerfile build context"


def _run_tool(args: list[str], ok_exit_codes: tuple[int, ...] = (0,)) -> tuple[VerifyStatus, str]:
    if shutil.which(args[0]) is None:
        return "skipped", f"{args[0]} not installed"
    completed = subprocess.run(args, capture_output=True, text=True)
    if completed.returncode in ok_exit_codes:
        return "passed", "ok"
    detail = (completed.stderr or completed.stdout or f"exit code {completed.returncode}").strip()
    return "failed", detail


def _verify_hadolint(context: VerifyContext) -> tuple[VerifyStatus, str]:
    return _run_tool(["hadolint", str(context.dockerfile_path)])


def _verify_trivy(context: VerifyContext) -> tuple[VerifyStatus, str]:
    targets, scope_label = _trivy_scan_targets(context)
    status, detail = _run_tool(
        [
            "trivy",
            "fs",
            "--severity",
            "HIGH,CRITICAL",
            "--exit-code",
            "1",
            "--no-progress",
            *[str(path) for path in targets],
        ],
    )
    if status != "passed":
        return status, detail
    scanned = ", ".join(str(path) for path in targets)
    return status, f"ok ({scope_label}: {scanned})"


def _verify_dive(context: VerifyContext) -> tuple[VerifyStatus, str]:
    if not context.image:
        return "skipped", "no image provided"
    return _run_tool(["dive", context.image, "--ci"])


def _verify_cosign(context: VerifyContext) -> tuple[VerifyStatus, str]:
    if not context.image:
        return "skipped", "no image provided"
    return _run_tool(["cosign", "verify", context.image])


def _verify_sbom(context: VerifyContext) -> tuple[VerifyStatus, str]:
    sbom = context.project_root / "sbom.spdx.json"
    if not sbom.exists():
        return "failed", f"missing SBOM file: {sbom}"
    try:
        payload = json.loads(sbom.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return "failed", f"invalid SBOM JSON: {exc}"
    if payload.get("spdxVersion") is None:
        return "failed", "SBOM missing spdxVersion field"
    return "passed", "spdx json detected"


def _verify_smoke(context: VerifyContext) -> tuple[VerifyStatus, str]:
    if not context.smoke_url:
        return "skipped", "no smoke URL provided"
    try:
        with urllib.request.urlopen(context.smoke_url, timeout=10) as response:
            body = response.read().decode("utf-8", errors="ignore")
            if response.status >= 400:
                return "failed", f"http status {response.status}"
            if "UP" in body:
                return "passed", "service reported UP"
            return "passed", f"http status {response.status}"
    except (TimeoutError, urllib.error.URLError) as exc:
        return "failed", str(exc)


def _verify_plugin_entry(context: VerifyContext, entry: Any) -> tuple[VerifyStatus, str]:
    loaded = entry.load()
    verifier = loaded() if isinstance(loaded, type) else loaded
    if hasattr(verifier, "verify") and callable(verifier.verify):
        result = verifier.verify(context)
    elif callable(verifier):
        result = verifier(context)
    else:
        raise TypeError("verifier plugin must define verify(context) or be callable")
    if isinstance(result, tuple) and len(result) == 2:
        status = cast(VerifyStatus, result[0])
        detail = str(result[1])
        if status not in {"passed", "failed", "skipped"}:
            raise ValueError("invalid plugin verifier status")
        return status, detail
    if isinstance(result, dict):
        status = cast(VerifyStatus, result.get("status"))
        detail = str(result.get("detail", ""))
        if status not in {"passed", "failed", "skipped"}:
            raise ValueError("invalid plugin verifier status")
        return status, detail
    raise TypeError("verifier plugin must return (status, detail) or a dict payload")


def _verify_config_checks(context: VerifyContext) -> list[VerifyResult]:
    from ..config import _resolve_build_tool, load_config
    from ..config_audit import load_config_audit
    from ..project_detect import inspect_project

    started = time.monotonic()
    build_tool = context.build_tool
    if build_tool is None:
        config_path = context.project_root / ".springdocker.toml"
        if config_path.is_file():
            loaded = load_config(config_path)
            build_tool = _resolve_build_tool(None, loaded, "project")
    if build_tool is None:
        try:
            build_tool = inspect_project(context.project_root, None).build_tool
        except ValueError as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            return [
                VerifyResult(
                    name="config-drift",
                    status="skipped",
                    detail=f"build tool could not be resolved: {exc}",
                    duration_ms=duration_ms,
                )
            ]

    audit = load_config_audit(context.project_root, build_tool, context.dockerfile_path)
    if audit is None:
        duration_ms = int((time.monotonic() - started) * 1000)
        return [
            VerifyResult(
                name="config-drift",
                status="skipped",
                detail="no .springdocker.toml present for config audit",
                duration_ms=duration_ms,
            )
        ]

    dockerfile_text = context.dockerfile_path.read_text(encoding="utf-8")
    from ..config_audit import run_config_verify_checks

    checks = run_config_verify_checks(audit, dockerfile_text)
    results: list[VerifyResult] = []
    for name, status, detail in checks:
        check_started = time.monotonic()
        duration_ms = int((time.monotonic() - check_started) * 1000)
        results.append(
            VerifyResult(
                name=name,
                status=cast(VerifyStatus, status),
                detail=detail,
                duration_ms=duration_ms,
            )
        )
    return results


def run_verification(context: VerifyContext) -> VerifyOutcome:
    checks: list[tuple[str, Any]] = [
        ("hadolint", _verify_hadolint),
        ("trivy", _verify_trivy),
        ("dive", _verify_dive),
        ("cosign", _verify_cosign),
        ("sbom", _verify_sbom),
        ("smoke", _verify_smoke),
    ]

    results: list[VerifyResult] = []
    for name, check in checks:
        started = time.monotonic()
        status, detail = check(context)
        duration_ms = int((time.monotonic() - started) * 1000)
        results.append(VerifyResult(name=name, status=status, detail=detail, duration_ms=duration_ms))

    if context.check_config_drift:
        results.extend(_verify_config_checks(context))

    for entry in iter_verifier_entry_points():
        started = time.monotonic()
        try:
            status, detail = _verify_plugin_entry(context, entry)
        except Exception as exc:
            status, detail = "failed", str(exc)
        duration_ms = int((time.monotonic() - started) * 1000)
        results.append(VerifyResult(name=f"plugin:{entry.name}", status=status, detail=detail, duration_ms=duration_ms))

    return VerifyOutcome(results=tuple(results))


def render_verify_table(outcome: VerifyOutcome) -> str:
    lines = ["| Check | Status | Detail | Duration (ms) |", "|---|---|---|---:|"]
    for result in outcome.results:
        lines.append(f"| {result.name} | {result.status} | {result.detail} | {result.duration_ms} |")
    lines.append(f"| overall | {'failed' if outcome.failed else 'passed'} | - | - |")
    return "\n".join(lines)


def render_verify_json(outcome: VerifyOutcome) -> str:
    payload = {
        "overall": "failed" if outcome.failed else "passed",
        "results": [
            {
                "name": item.name,
                "status": item.status,
                "detail": item.detail,
                "duration_ms": item.duration_ms,
            }
            for item in outcome.results
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def render_verify_junit(outcome: VerifyOutcome) -> str:
    cases: list[str] = []
    failures = 0
    skipped = 0
    for item in outcome.results:
        if item.status == "failed":
            failures += 1
        if item.status == "skipped":
            skipped += 1
        case = [f'<testcase classname="springdocker.verify" name="{escape(item.name)}" time="{item.duration_ms / 1000:.3f}">']
        if item.status == "failed":
            case.append(f'<failure message="{escape(item.detail)}"/>')
        elif item.status == "skipped":
            case.append(f'<skipped message="{escape(item.detail)}"/>')
        case.append("</testcase>")
        cases.append("".join(case))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<testsuite name="springdocker.verify" tests="{len(outcome.results)}" failures="{failures}" skipped="{skipped}">'
        + "".join(cases)
        + "</testsuite>"
    )


def render_verify_sarif(outcome: VerifyOutcome) -> str:
    level_map = {"failed": "error", "passed": "note", "skipped": "warning"}
    results = [
        {
            "ruleId": item.name,
            "level": level_map[item.status],
            "message": {"text": item.detail or item.status},
        }
        for item in outcome.results
    ]
    payload = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {"driver": {"name": "springdocker verify"}},
                "results": results,
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)
