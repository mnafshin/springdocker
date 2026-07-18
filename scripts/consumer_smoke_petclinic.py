#!/usr/bin/env python3
"""Consumer smoke: PyPI-style onboarding on spring-petclinic, then docker build + readiness.

Runs the documented first-time workflow against a pinned upstream Spring Boot sample:

  setup (--profile build-speed) → verify --check-config-drift → docker build

Clone spring-projects/spring-petclinic at the commit in consumer_smoke_petclinic.manifest.json.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from springdocker.benchmarks.runner import _run_command, _stop_container, _wait_readiness

MANIFEST_PATH = Path(__file__).with_name("consumer_smoke_petclinic.manifest.json")
MINIMAL_SBOM = {
    "spdxVersion": "SPDX-2.3",
    "name": "spring-petclinic-consumer-smoke",
    "comment": "Placeholder SPDX document for springdocker verify in consumer-smoke only.",
}


@dataclass(frozen=True)
class ConsumerSmokeManifest:
    repository: str
    ref: str
    build_tool: str
    dockerfile: str
    image: str
    host_port: int
    container_port: int
    readiness_path: str
    configure_wizard_input: str
    build_timeout_seconds: int
    readiness_timeout_seconds: float

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> ConsumerSmokeManifest:
        return cls(
            repository=str(payload["repository"]),
            ref=str(payload["ref"]),
            build_tool=str(payload["build_tool"]),
            dockerfile=str(payload["dockerfile"]),
            image=str(payload["image"]),
            host_port=int(payload["host_port"]),
            container_port=int(payload["container_port"]),
            readiness_path=str(payload["readiness_path"]),
            configure_wizard_input=str(payload.get("configure_wizard_input", "\n\n")),
            build_timeout_seconds=int(payload.get("build_timeout_seconds", 3600)),
            readiness_timeout_seconds=float(payload.get("readiness_timeout_seconds", 180.0)),
        )


def load_manifest(path: Path = MANIFEST_PATH) -> ConsumerSmokeManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return ConsumerSmokeManifest.from_mapping(payload)


def ensure_sbom_placeholder(project_root: Path) -> Path:
    """verify checks project SBOM when include_embedded_sbom is enabled in config."""
    destination = project_root / "sbom.spdx.json"
    if not destination.exists():
        destination.write_text(json.dumps(MINIMAL_SBOM, indent=2) + "\n", encoding="utf-8")
        print(f"-- wrote placeholder SBOM: {destination}")
    return destination


def clone_petclinic(repository: str, ref: str, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    print(f"-- clone {repository} @ {ref[:12]}")
    clone = _run_command(
        ["git", "clone", "--filter=blob:none", "--no-checkout", repository, str(destination)],
        timeout_seconds=300,
        capture_output=True,
    )
    if clone.returncode != 0:
        detail = (clone.stderr or clone.stdout or clone.detail or "git clone failed").strip()
        raise RuntimeError(detail)

    fetch = _run_command(
        ["git", "fetch", "--depth", "1", "origin", ref],
        cwd=destination,
        timeout_seconds=300,
        capture_output=True,
    )
    if fetch.returncode != 0:
        detail = (fetch.stderr or fetch.stdout or fetch.detail or "git fetch failed").strip()
        raise RuntimeError(detail)

    checkout = _run_command(
        ["git", "checkout", "--detach", ref],
        cwd=destination,
        timeout_seconds=120,
        capture_output=True,
    )
    if checkout.returncode != 0:
        detail = (checkout.stderr or checkout.stdout or checkout.detail or "git checkout failed").strip()
        raise RuntimeError(detail)


def _run_springdocker(
    springdocker_cmd: list[str],
    cli_args: list[str],
    *,
    project_root: Path,
    input_text: str | None = None,
    capture_output: bool = False,
) -> int | tuple[int, str]:
    command = [*springdocker_cmd, *cli_args, "--project-root", str(project_root)]
    print(f"-- {' '.join(command)}")
    completed = subprocess.run(
        command,
        input=input_text,
        text=True,
        check=False,
        capture_output=capture_output,
    )
    if capture_output:
        return completed.returncode, completed.stdout
    return completed.returncode


def run_onboarding_workflow(
    project_root: Path,
    manifest: ConsumerSmokeManifest,
    *,
    springdocker_cmd: list[str],
) -> int:
    print("\n== onboarding: setup")
    code = _run_springdocker(
        springdocker_cmd,
        [
            "setup",
            "--force",
            "--profile",
            "build-speed",
            "--build-tool",
            manifest.build_tool,
            "--output",
            manifest.dockerfile,
        ],
        project_root=project_root,
    )
    if code != 0:
        print(f"onboarding step failed: setup (exit {code})", file=sys.stderr)
        return code

    ensure_sbom_placeholder(project_root)

    dockerfile_path = project_root / manifest.dockerfile
    if not dockerfile_path.is_file():
        print(f"missing generated Dockerfile: {dockerfile_path}", file=sys.stderr)
        return 1

    print("\n== onboarding: verify --check-config-drift")
    verify_result = _run_springdocker(
        springdocker_cmd,
        [
            "verify",
            "--dockerfile",
            manifest.dockerfile,
            "--check-config-drift",
            "--build-tool",
            manifest.build_tool,
            "--format",
            "json",
        ],
        project_root=project_root,
        capture_output=True,
    )
    if isinstance(verify_result, tuple):
        code, stdout = verify_result
    else:
        code, stdout = verify_result, ""
    if code != 0:
        if stdout:
            print(stdout, file=sys.stderr)
        return code
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        print("verify did not emit valid JSON", file=sys.stderr)
        return 1
    checks = {item["name"]: item for item in payload.get("results", [])}
    drift = checks.get("config-drift")
    if drift is None:
        print("verify JSON missing config-drift check", file=sys.stderr)
        return 1
    if drift.get("status") != "passed":
        print(f"config-drift check failed: {drift}", file=sys.stderr)
        return 1
    if payload.get("overall") != "passed":
        print(f"verify overall failed: {payload.get('overall')}", file=sys.stderr)
        return 1
    print("verify ok (config-drift passed)")
    return 0


def docker_build(project_root: Path, dockerfile: str, image: str, timeout_seconds: int) -> int:
    print(f"\n== docker build: {image}")
    result = _run_command(
        ["docker", "build", "-f", dockerfile, "-t", image, "."],
        cwd=project_root,
        timeout_seconds=timeout_seconds,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or result.detail or "docker build failed").strip()
        print(detail, file=sys.stderr)
    return result.returncode


def probe_readiness(
    image: str,
    *,
    host_port: int,
    container_port: int,
    readiness_path: str,
    timeout_seconds: float,
) -> int:
    container_name = f"springdocker-consumer-petclinic-{uuid.uuid4().hex[:12]}"
    readiness_url = f"http://localhost:{host_port}{readiness_path}"
    print(f"\n== docker run readiness probe: {readiness_url}")

    start = _run_command(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container_name,
            "-p",
            f"{host_port}:{container_port}",
            image,
        ],
        timeout_seconds=120,
        capture_output=True,
    )
    if start.returncode != 0:
        detail = (start.stderr or start.stdout or start.detail or "docker run failed").strip()
        print(detail, file=sys.stderr)
        return start.returncode

    try:
        startup_ms = _wait_readiness(readiness_url, timeout_seconds=timeout_seconds)
        if startup_ms < 0:
            print(
                f"readiness probe failed: {readiness_url} did not return HTTP success within {timeout_seconds:.0f}s",
                file=sys.stderr,
            )
            return 1
        print(f"readiness probe ok: startup_ms={startup_ms}")
        return 0
    finally:
        _stop_container(container_name)


def resolve_springdocker_cmd(explicit: str | None) -> list[str]:
    if explicit:
        return explicit.split()
    if shutil.which("springdocker"):
        return ["springdocker"]
    raise RuntimeError(
        "springdocker not found on PATH; install with `pip install -e .` or pass --springdocker-cmd"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  pip install -e .\n"
            "  DOCKER_BUILDKIT=1 python scripts/consumer_smoke_petclinic.py\n\n"
            "  pipx install springdocker\n"
            "  DOCKER_BUILDKIT=1 python scripts/consumer_smoke_petclinic.py --springdocker-cmd springdocker\n"
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help="Pinned upstream project manifest (default: scripts/consumer_smoke_petclinic.manifest.json)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Directory for cloned petclinic (default: temp dir; removed unless --keep-work-dir)",
    )
    parser.add_argument(
        "--keep-work-dir",
        action="store_true",
        help="Keep cloned project directory after the run (implies a persistent --work-dir when set)",
    )
    parser.add_argument(
        "--skip-clone",
        action="store_true",
        help="Reuse --work-dir without cloning (project must already exist)",
    )
    parser.add_argument(
        "--skip-docker-build",
        action="store_true",
        help="Stop after verify (onboarding workflow only)",
    )
    parser.add_argument(
        "--skip-readiness",
        action="store_true",
        help="Build image but skip container run/readiness probe",
    )
    parser.add_argument(
        "--springdocker-cmd",
        default=None,
        help="springdocker executable or command prefix (default: springdocker on PATH)",
    )
    args = parser.parse_args(argv)

    if shutil.which("docker") is None:
        print("docker not found on PATH", file=sys.stderr)
        return 1
    if shutil.which("git") is None:
        print("git not found on PATH", file=sys.stderr)
        return 1

    try:
        manifest = load_manifest(args.manifest.resolve())
        springdocker_cmd = resolve_springdocker_cmd(args.springdocker_cmd)
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    project_root = args.work_dir
    if project_root is None:
        if args.keep_work_dir:
            project_root = Path.cwd() / ".consumer-smoke-petclinic"
        else:
            temp_dir = tempfile.TemporaryDirectory(prefix="springdocker-consumer-smoke-")
            project_root = Path(temp_dir.name) / "spring-petclinic"
    project_root = project_root.resolve()

    try:
        if not args.skip_clone:
            clone_petclinic(manifest.repository, manifest.ref, project_root)
        elif not project_root.is_dir():
            print(f"missing project root (--skip-clone): {project_root}", file=sys.stderr)
            return 1

        print(f"\n== project root: {project_root}")
        onboarding_code = run_onboarding_workflow(project_root, manifest, springdocker_cmd=springdocker_cmd)
        if onboarding_code != 0:
            return onboarding_code

        if args.skip_docker_build:
            print("\nconsumer smoke ok (onboarding only)")
            return 0

        build_code = docker_build(
            project_root,
            manifest.dockerfile,
            manifest.image,
            manifest.build_timeout_seconds,
        )
        if build_code != 0:
            print(f"docker build failed (exit {build_code})", file=sys.stderr)
            return build_code

        if args.skip_readiness:
            print("\nconsumer smoke ok (docker build only)")
            return 0

        readiness_code = probe_readiness(
            manifest.image,
            host_port=manifest.host_port,
            container_port=manifest.container_port,
            readiness_path=manifest.readiness_path,
            timeout_seconds=manifest.readiness_timeout_seconds,
        )
        if readiness_code != 0:
            return readiness_code

        print("\nconsumer smoke ok (onboarding + docker build + readiness)")
        return 0
    finally:
        if args.keep_work_dir:
            print(f"\n-- kept work dir: {project_root}")
        elif temp_dir is not None:
            temp_dir.cleanup()


def _exit_code_from_main(argv: list[str] | None = None) -> int:
    try:
        return main(argv)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(_exit_code_from_main())
