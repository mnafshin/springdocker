#!/usr/bin/env python3
"""Check out the pinned java-spring-docker-sample into samples/java-spring-docker.

Resolution order:
  1. JAVA_SPRING_DOCKER_SAMPLE_ROOT — use that local tree (symlink when possible)
  2. Sibling directory ../java-spring-docker-sample (common local layout)
  3. Clone the GitHub repository at the pinned ref in the manifest

CI and local contributors run this before docker-smoke / benchmark jobs that need
the full Spring Boot sample. Minimal fixtures under tests/fixtures/ do not need it.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from springdocker.benchmarks.runner import _run_command

MANIFEST_PATH = Path(__file__).with_name("java_spring_docker_sample.manifest.json")
REPO_ROOT = Path(__file__).resolve().parents[1]


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return payload


def _looks_like_sample(path: Path) -> bool:
    return path.is_dir() and (path / "pom.xml").is_file() and (path / "build.gradle").is_file()


def resolve_local_source(manifest: dict[str, Any]) -> Path | None:
    env = os.environ.get("JAVA_SPRING_DOCKER_SAMPLE_ROOT", "").strip()
    if env:
        candidate = Path(env).expanduser().resolve()
        if not _looks_like_sample(candidate):
            raise RuntimeError(
                f"JAVA_SPRING_DOCKER_SAMPLE_ROOT is set but does not look like the sample: {candidate}"
            )
        return candidate

    sibling_name = str(manifest.get("sibling_dirname") or "java-spring-docker-sample")
    sibling = (REPO_ROOT.parent / sibling_name).resolve()
    if _looks_like_sample(sibling):
        return sibling
    return None


def clone_sample(repository: str, ref: str, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
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


def link_or_copy_local(source: Path, destination: Path) -> None:
    source = source.resolve()
    if destination.exists() or destination.is_symlink():
        try:
            if destination.resolve() == source:
                print(f"-- sample already at {destination}")
                return
        except OSError:
            pass
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.symlink_to(source, target_is_directory=True)
        print(f"-- symlinked {destination} -> {source}")
    except OSError:
        print(f"-- copy {source} -> {destination}")
        shutil.copytree(source, destination)


def ensure_sample(
    *,
    destination: Path | None = None,
    force_remote: bool = False,
    manifest_path: Path = MANIFEST_PATH,
) -> Path:
    manifest = load_manifest(manifest_path)
    checkout_rel = str(manifest.get("checkout_path") or "samples/java-spring-docker")
    dest = destination if destination is not None else REPO_ROOT / checkout_rel
    if not dest.is_absolute():
        dest = REPO_ROOT / dest

    if not force_remote:
        local = resolve_local_source(manifest)
        if local is not None:
            link_or_copy_local(local, dest)
            return dest

    repository = str(manifest["repository"])
    ref = str(manifest["ref"])
    clone_sample(repository, ref, dest)
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        type=Path,
        default=None,
        help="Checkout path (default: samples/java-spring-docker from manifest)",
    )
    parser.add_argument(
        "--force-remote",
        action="store_true",
        help="Ignore local sibling / JAVA_SPRING_DOCKER_SAMPLE_ROOT and clone the pinned ref",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help="Path to java_spring_docker_sample.manifest.json",
    )
    args = parser.parse_args(argv)

    try:
        path = ensure_sample(
            destination=args.destination,
            force_remote=args.force_remote,
            manifest_path=args.manifest,
        )
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"checkout_sample failed: {exc}", file=sys.stderr)
        return 1

    print(f"sample ready: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
