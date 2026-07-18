#!/usr/bin/env python3
"""Build a springdocker-generated Dockerfile on a real Docker daemon and probe readiness."""

from __future__ import annotations

import argparse
import subprocess
import sys
import uuid
from pathlib import Path

from springdocker.benchmarks.runner import _run_command, _stop_container, _wait_readiness

DEFAULT_PROJECT_ROOT = Path("samples/java-spring-docker")
DEFAULT_DOCKERFILE = "Dockerfile.ci-smoke"
DEFAULT_IMAGE = "springdocker-ci-smoke:latest"
DEFAULT_HOST_PORT = 18081
READINESS_PATH = "/actuator/health/readiness"
BUILD_TIMEOUT_SECONDS = 1200
READINESS_TIMEOUT_SECONDS = 120.0


def _run_springdocker(args: list[str], project_root: Path) -> int:
    completed = subprocess.run(
        ["springdocker", *args, "--project-root", str(project_root)],
        check=False,
    )
    return completed.returncode


def _generate_dockerfile(project_root: Path, dockerfile: str) -> int:
    print(f"-- generate Dockerfile: {dockerfile}")
    return _run_springdocker(
        ["dockerfile", "generate", "--output", dockerfile],
        project_root,
    )


def _docker_build(
    project_root: Path,
    dockerfile: str,
    image: str,
    timeout_seconds: int,
) -> int:
    print(f"-- docker build: {image}")
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


def _probe_readiness(image: str, host_port: int, timeout_seconds: float) -> int:
    container_name = f"springdocker-ci-smoke-{uuid.uuid4().hex[:12]}"
    readiness_url = f"http://localhost:{host_port}{READINESS_PATH}"
    print(f"-- docker run readiness probe: {readiness_url}")

    start = _run_command(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container_name,
            "-p",
            f"{host_port}:8081",
            image,
        ],
        timeout_seconds=60,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=DEFAULT_PROJECT_ROOT,
        help="Spring Boot project used for smoke build (default: samples/java-spring-docker after checkout_sample.py)",
    )
    parser.add_argument(
        "--dockerfile",
        default=DEFAULT_DOCKERFILE,
        help="Generated Dockerfile path relative to project root",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image tag to build")
    parser.add_argument("--host-port", type=int, default=DEFAULT_HOST_PORT, help="Host port mapped to management port 8081")
    parser.add_argument(
        "--build-timeout-seconds",
        type=int,
        default=BUILD_TIMEOUT_SECONDS,
        help="Maximum seconds to wait for docker build",
    )
    parser.add_argument(
        "--readiness-timeout-seconds",
        type=float,
        default=READINESS_TIMEOUT_SECONDS,
        help="Maximum seconds to wait for actuator readiness after container start",
    )
    parser.add_argument(
        "--skip-readiness",
        action="store_true",
        help="Only verify docker build succeeds (skip container run/readiness probe)",
    )
    args = parser.parse_args(argv)

    project_root = args.project_root.resolve()
    if not project_root.is_dir():
        print(f"missing project root: {project_root}", file=sys.stderr)
        return 1

    generate_code = _generate_dockerfile(project_root, args.dockerfile)
    if generate_code != 0:
        return generate_code

    build_code = _docker_build(project_root, args.dockerfile, args.image, args.build_timeout_seconds)
    if build_code != 0:
        return build_code

    if args.skip_readiness:
        print("docker build ok (readiness probe skipped)")
        return 0

    return _probe_readiness(args.image, args.host_port, args.readiness_timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
