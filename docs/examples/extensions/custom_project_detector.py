from __future__ import annotations

from pathlib import Path


def detect_build_tool(project_root: Path) -> str | None:
    """Example: prefer Gradle when both settings and wrapper exist (non-standard layouts)."""
    if (project_root / "gradle.properties").exists() and (project_root / "settings.gradle").exists():
        return "gradle"
    return None
