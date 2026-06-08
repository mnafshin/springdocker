from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..dockerfile import JLINK_BASELINE_MODULES, DockerfileOptions, build_dockerfile, explain_dockerfile_text
from ..plugins import apply_dockerfile_mutators, render_recipe_from_plugins

DEFAULT_DOCKERIGNORE = (
    ".git",
    ".gitignore",
    ".venv",
    "__pycache__",
    "*.pyc",
    "target",
    "build",
    ".idea",
    ".vscode",
    ".DS_Store",
)


def resolve_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = project_root / path
    return path


def parse_must_have_modules(project_root: Path, must_have_modules_file: str | None) -> tuple[str, ...]:
    if not must_have_modules_file:
        return ()
    modules_path = resolve_path(project_root, must_have_modules_file)
    if not modules_path.exists():
        raise ValueError(f"missing must-have modules file: {modules_path}")
    parsed: list[str] = []
    seen: set[str] = set()
    for line in modules_path.read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if not entry:
            continue
        for token in [part.strip() for part in entry.split(",")]:
            if not token:
                continue
            if not re.fullmatch(r"[A-Za-z0-9._-]+", token):
                raise ValueError(f"invalid module name in {modules_path}: {token}")
            if token not in seen:
                parsed.append(token)
                seen.add(token)
    return tuple(parsed)


def _project_has_actuator_dependency(project_root: Path) -> bool:
    for descriptor in ("pom.xml", "build.gradle", "build.gradle.kts"):
        path = project_root / descriptor
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "spring-boot-starter-actuator" in text:
            return True
    return False


def ensure_default_dockerignore(project_root: Path) -> Path:
    destination = project_root / ".dockerignore"
    if destination.exists():
        return destination
    destination.write_text("\n".join(DEFAULT_DOCKERIGNORE) + "\n", encoding="utf-8")
    return destination


def generate_dockerfile(
    project_root: Path,
    output_path: str,
    build_tool: str,
    java_version: int,
    must_have_modules_file: str | None,
    jlink_baseline_modules: tuple[str, ...] = JLINK_BASELINE_MODULES,
    recipe: str = "jvm-balanced",
) -> GeneratedDockerfile:
    must_have_modules = parse_must_have_modules(project_root, must_have_modules_file)
    actuator_healthcheck = "/actuator/health/readiness" if _project_has_actuator_dependency(project_root) else None
    options = DockerfileOptions(
        build_tool=build_tool,
        recipe=recipe,
        java_version=java_version,
        must_have_modules=must_have_modules,
        jlink_baseline_modules=jlink_baseline_modules,
        healthcheck_path=actuator_healthcheck,
    )
    recipe_warnings: tuple[str, ...] = ()
    if recipe in {"jvm-balanced", "spring-aot", "native-aot"}:
        rendered = build_dockerfile(options)
    else:
        recipe_render = render_recipe_from_plugins(recipe=recipe, options=options)
        recipe_warnings = recipe_render.warnings
        if recipe_render.handled and recipe_render.rendered is not None:
            rendered = recipe_render.rendered
        elif recipe_render.handled:
            raise ValueError(f"recipe plugin '{recipe}' failed to render Dockerfile")
        else:
            raise ValueError(f"unknown dockerfile recipe: {recipe}")

    generated = apply_dockerfile_mutators(
        dockerfile_text=rendered,
        options=options,
    )
    destination = resolve_path(project_root, output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(generated.dockerfile_text, encoding="utf-8")
    ensure_default_dockerignore(project_root)
    return GeneratedDockerfile(path=destination, plugin_warnings=(*recipe_warnings, *generated.warnings))


@dataclass(frozen=True)
class GeneratedDockerfile:
    path: Path
    plugin_warnings: tuple[str, ...]


def explain_dockerfile(project_root: Path, dockerfile_path: str) -> dict[str, object]:
    path = resolve_path(project_root, dockerfile_path)
    if not path.exists():
        raise ValueError(f"missing Dockerfile: {path}")
    payload = dict(explain_dockerfile_text(path.read_text(encoding="utf-8")))
    payload["path"] = str(path)
    return payload
