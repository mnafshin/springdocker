"""Detect Gradle monorepos where the wrapper lives at root but Boot app is nested."""

from __future__ import annotations

from pathlib import Path


def detect_build_tool(project_root: Path) -> str | None:
    if not (project_root / "gradlew").exists():
        return None
    for candidate in ("settings.gradle.kts", "settings.gradle"):
        settings = project_root / candidate
        if not settings.exists():
            continue
        text = settings.read_text(encoding="utf-8", errors="ignore")
        if "include(" in text or "include '" in text:
            return "gradle"
    return None
