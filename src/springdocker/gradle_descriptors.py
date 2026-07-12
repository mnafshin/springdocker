"""Gradle descriptor file resolution for Dockerfile COPY stages."""

from __future__ import annotations

from pathlib import Path

DEFAULT_GRADLE_DESCRIPTOR_FILES: tuple[str, ...] = ("build.gradle", "settings.gradle")


def resolve_gradle_descriptor_files(root: Path) -> tuple[str, ...]:
    """Return Gradle root descriptor paths to COPY into the Dockerfile build stage."""
    build_files = [name for name in ("build.gradle", "build.gradle.kts") if (root / name).exists()]
    settings_files = [name for name in ("settings.gradle", "settings.gradle.kts") if (root / name).exists()]
    optional = [name for name in ("gradle.properties", "gradle/libs.versions.toml") if (root / name).exists()]
    if not build_files and not settings_files:
        return DEFAULT_GRADLE_DESCRIPTOR_FILES
    return tuple([*build_files, *settings_files, *optional])
