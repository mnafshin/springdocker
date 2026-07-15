from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..config import HEALTHCHECK_AUTO, DockerfileGenerateConfig
from ..dockerfile import (
    BUILTIN_RECIPES,
    JLINK_BASELINE_MODULES,
    NATIVE_AOT_SCAFFOLD_WARNING,
    DockerfileOptions,
    build_dockerfile,
)
from ..dockerfile_explain import explain_dockerfile_text
from ..gradle_descriptors import resolve_gradle_descriptor_files
from ..java_features import validate_dockerfile_options
from ..plugins import apply_dockerfile_mutators, render_recipe_from_plugins
from ..project_detect import has_spring_web_dependency

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


def _resolve_jlink_baseline_modules(
    configured: tuple[str, ...] | None,
    project_root: Path,
) -> tuple[str, ...]:
    if configured is not None:
        return configured
    return JLINK_BASELINE_MODULES if has_spring_web_dependency(project_root) else ()


def _resolve_healthcheck_path(
    configured: str,
    project_root: Path,
) -> str | None:
    if configured == HEALTHCHECK_AUTO:
        return "/actuator/health/readiness" if _project_has_actuator_dependency(project_root) else None
    if configured == "":
        return None
    return configured


def dockerfile_options_from_config(
    project_root: Path,
    build_tool: str,
    config: DockerfileGenerateConfig,
) -> DockerfileOptions:
    must_have_modules = parse_must_have_modules(project_root, config.must_have_modules_file)
    healthcheck_path = _resolve_healthcheck_path(config.healthcheck_path, project_root)
    jlink_baseline_modules = _resolve_jlink_baseline_modules(config.jlink_baseline_modules, project_root)
    gradle_descriptor_files = resolve_gradle_descriptor_files(project_root) if build_tool == "gradle" else ()
    options = DockerfileOptions(
        build_tool=build_tool,
        recipe=config.recipe,
        java_version=config.java_version,
        must_have_modules=must_have_modules,
        jlink_baseline_modules=jlink_baseline_modules,
        runtime_image=config.runtime_image,
        use_buildkit_cache=config.use_buildkit_cache,
        use_jlink=config.use_jlink,
        use_layered_jar=config.use_layered_jar,
        non_root=config.non_root,
        platform_aware=config.platform_aware,
        enable_appcds=config.enable_appcds,
        enable_jep483_aot_cache=config.enable_jep483_aot_cache,
        include_oci_labels=config.include_oci_labels,
        include_stopsignal=config.include_stopsignal,
        include_embedded_sbom=config.include_embedded_sbom,
        include_reproducible_controls=config.include_reproducible_controls,
        pin_digests=config.pin_digests,
        tuned_jvm_flags=config.tuned_jvm_flags,
        jvm_flags=config.jvm_flags,
        healthcheck_path=healthcheck_path,
        gradle_descriptor_files=gradle_descriptor_files,
    )
    validate_dockerfile_options(options)
    return options


def generate_dockerfile(
    project_root: Path,
    output_path: str,
    build_tool: str,
    java_version: int,
    must_have_modules_file: str | None,
    jlink_baseline_modules: tuple[str, ...] | None = None,
    recipe: str = "jvm-balanced",
) -> GeneratedDockerfile:
    config = DockerfileGenerateConfig(
        build_tool=build_tool,
        output=output_path,
        java_version=java_version,
        recipe=recipe,
        profile=None,
        must_have_modules_file=must_have_modules_file,
        jlink_baseline_modules=jlink_baseline_modules,
        runtime_image="distroless",
        use_buildkit_cache=True,
        use_jlink=True,
        use_layered_jar=True,
        non_root=True,
        platform_aware=True,
        enable_appcds=True,
        enable_jep483_aot_cache=False,
        include_oci_labels=True,
        include_stopsignal=True,
        include_embedded_sbom=True,
        include_reproducible_controls=True,
        pin_digests=True,
        tuned_jvm_flags=True,
        jvm_flags=(),
        healthcheck_path=HEALTHCHECK_AUTO,
    )
    return generate_dockerfile_from_config(project_root, config, build_tool)


def _render_dockerfile_from_config(
    project_root: Path,
    config: DockerfileGenerateConfig,
    build_tool: str,
) -> tuple[str, tuple[str, ...]]:
    options = dockerfile_options_from_config(project_root, build_tool, config)
    recipe = config.recipe
    if recipe in BUILTIN_RECIPES:
        rendered = build_dockerfile(options)
    else:
        recipe_render = render_recipe_from_plugins(recipe=recipe, options=options)
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
    return generated.dockerfile_text, generated.warnings


def render_dockerfile_text_from_config(
    project_root: Path,
    config: DockerfileGenerateConfig,
    build_tool: str,
) -> str:
    rendered_text, _ = _render_dockerfile_from_config(project_root, config, build_tool)
    return rendered_text


def generate_dockerfile_from_config(
    project_root: Path,
    config: DockerfileGenerateConfig,
    build_tool: str,
) -> GeneratedDockerfile:
    recipe = config.recipe
    recipe_warnings: tuple[str, ...] = ()
    scaffold_warnings: tuple[str, ...] = ()
    if recipe == "native-aot":
        scaffold_warnings = (NATIVE_AOT_SCAFFOLD_WARNING,)
    if recipe not in BUILTIN_RECIPES:
        options = dockerfile_options_from_config(project_root, build_tool, config)
        recipe_render = render_recipe_from_plugins(recipe=recipe, options=options)
        recipe_warnings = recipe_render.warnings

    rendered_text, mutator_warnings = _render_dockerfile_from_config(project_root, config, build_tool)
    destination = resolve_path(project_root, config.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered_text, encoding="utf-8")
    ensure_default_dockerignore(project_root)
    return GeneratedDockerfile(
        path=destination,
        plugin_warnings=(*scaffold_warnings, *recipe_warnings, *mutator_warnings),
    )


@dataclass(frozen=True)
class GeneratedDockerfile:
    path: Path
    plugin_warnings: tuple[str, ...]


def explain_dockerfile(
    project_root: Path,
    dockerfile_path: str,
    *,
    config_aware: bool = False,
    build_tool: str | None = None,
) -> dict[str, object]:
    path = resolve_path(project_root, dockerfile_path)
    if not path.exists():
        raise ValueError(f"missing Dockerfile: {path}")
    payload = dict(explain_dockerfile_text(path.read_text(encoding="utf-8")))
    payload["path"] = str(path)
    if not config_aware:
        return payload

    from ..config_audit import build_config_aware_payload, load_config_audit
    from ..project_detect import inspect_project

    resolved_build_tool = build_tool
    if resolved_build_tool is None:
        try:
            resolved_build_tool = inspect_project(project_root, None).build_tool
        except ValueError:
            resolved_build_tool = None

    if resolved_build_tool is None:
        payload["config_aware"] = {
            "config_present": False,
            "detail": "build tool could not be resolved for config audit",
        }
        return payload

    audit = load_config_audit(project_root, resolved_build_tool, path)
    if audit is None:
        payload["config_aware"] = {"config_present": False}
        return payload

    payload["config_aware"] = build_config_aware_payload(audit)
    return payload
