"""Connect explain/verify output to `.springdocker.toml` SSOT."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from springdocker.config import (
    DockerfileGenerateConfig,
    load_config,
    resolve_dockerfile_generate_config,
)
from springdocker.dockerfile import DockerfileOptions
from springdocker.services import dockerfile_service

_OPTION_SOURCE_KEYS: tuple[str, ...] = (
    "java_version",
    "recipe",
    "profile",
    "must_have_modules_file",
    "jlink_baseline_modules",
    "runtime_image",
    "use_buildkit_cache",
    "use_jlink",
    "use_layered_jar",
    "non_root",
    "platform_aware",
    "enable_appcds",
    "enable_jep483_aot_cache",
    "include_oci_labels",
    "include_stopsignal",
    "include_embedded_sbom",
    "include_reproducible_controls",
    "pin_digests",
    "tuned_jvm_flags",
    "jvm_flags",
    "healthcheck_path",
)


@dataclass(frozen=True)
class DriftResult:
    detected: bool
    detail: str


@dataclass(frozen=True)
class ConfigAudit:
    config_path: Path
    resolved_config: DockerfileGenerateConfig
    resolved_options: DockerfileOptions
    option_sources: dict[str, str]
    drift: DriftResult


def normalize_dockerfile_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _relative_output_path(project_root: Path, dockerfile_path: Path) -> str:
    try:
        return str(dockerfile_path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(dockerfile_path)


def resolve_dockerfile_audit_config(
    project_root: Path,
    build_tool: str | None,
    dockerfile_path: Path,
    loaded_config: dict[str, Any],
) -> DockerfileGenerateConfig:
    from springdocker.project_detect import inspect_project_details

    output = _relative_output_path(project_root, dockerfile_path)
    detected_java: int | None = None
    try:
        detected_java = inspect_project_details(project_root, build_tool).java_version
    except ValueError:
        detected_java = None
    return resolve_dockerfile_generate_config(
        cli_build_tool=build_tool,
        cli_output=output,
        cli_java_version=None,
        cli_recipe=None,
        cli_profile=None,
        cli_runtime_image=None,
        cli_use_buildkit_cache=None,
        cli_use_jlink=None,
        cli_use_layered_jar=None,
        cli_non_root=None,
        cli_platform_aware=None,
        cli_enable_appcds=None,
        cli_enable_jep483_aot_cache=None,
        cli_include_oci_labels=None,
        cli_include_stopsignal=None,
        cli_include_embedded_sbom=None,
        cli_include_reproducible_controls=None,
        cli_pin_digests=None,
        cli_tuned_jvm_flags=None,
        cli_jvm_flags=None,
        cli_healthcheck_path=None,
        loaded_config=loaded_config,
        detected_java_version=detected_java,
    )


def option_sources_from_config(loaded_config: dict[str, Any]) -> dict[str, str]:
    dockerfile_section = loaded_config.get("dockerfile", {})
    configured_keys = set(dockerfile_section.keys()) if isinstance(dockerfile_section, dict) else set()
    sources: dict[str, str] = {}
    for key in _OPTION_SOURCE_KEYS:
        if key in configured_keys:
            sources[key] = "project"
        else:
            sources[key] = "default"
    return sources


def dockerfile_options_to_payload(options: DockerfileOptions) -> dict[str, object]:
    return {
        "build_tool": options.build_tool,
        "recipe": options.recipe,
        "java_version": options.java_version,
        "runtime_image": options.runtime_image,
        "use_buildkit_cache": options.use_buildkit_cache,
        "use_jlink": options.use_jlink,
        "use_layered_jar": options.use_layered_jar,
        "non_root": options.non_root,
        "platform_aware": options.platform_aware,
        "enable_appcds": options.enable_appcds,
        "enable_jep483_aot_cache": options.enable_jep483_aot_cache,
        "include_oci_labels": options.include_oci_labels,
        "include_stopsignal": options.include_stopsignal,
        "include_embedded_sbom": options.include_embedded_sbom,
        "include_reproducible_controls": options.include_reproducible_controls,
        "pin_digests": options.pin_digests,
        "tuned_jvm_flags": options.tuned_jvm_flags,
        "jvm_flags": list(options.jvm_flags),
        "resolved_jvm_flags": list(options.resolved_jvm_flags()),
        "must_have_modules": list(options.must_have_modules),
        "jlink_baseline_modules": list(options.jlink_baseline_modules),
        "healthcheck_path": options.healthcheck_path,
    }


def detect_config_drift(actual_text: str, expected_text: str) -> DriftResult:
    if normalize_dockerfile_text(actual_text) == normalize_dockerfile_text(expected_text):
        return DriftResult(detected=False, detail="Dockerfile matches config-driven generator output")
    return DriftResult(
        detected=True,
        detail="Dockerfile differs from `springdocker dockerfile generate` output for the current config",
    )


def load_config_audit(
    project_root: Path,
    build_tool: str,
    dockerfile_path: Path,
    *,
    config_path: Path | None = None,
) -> ConfigAudit | None:
    path = config_path or (project_root / ".springdocker.toml")
    if not path.exists():
        return None
    loaded_config = load_config(path)
    resolved_config = resolve_dockerfile_audit_config(project_root, build_tool, dockerfile_path, loaded_config)
    resolved_options = dockerfile_service.dockerfile_options_from_config(
        project_root,
        build_tool,
        resolved_config,
    )
    expected_text = dockerfile_service.render_dockerfile_text_from_config(
        project_root,
        resolved_config,
        build_tool,
    )
    actual_text = dockerfile_path.read_text(encoding="utf-8")
    return ConfigAudit(
        config_path=path,
        resolved_config=resolved_config,
        resolved_options=resolved_options,
        option_sources=option_sources_from_config(loaded_config),
        drift=detect_config_drift(actual_text, expected_text),
    )


def build_config_aware_payload(audit: ConfigAudit) -> dict[str, object]:
    return {
        "config_path": str(audit.config_path),
        "config_present": True,
        "resolved_options": dockerfile_options_to_payload(audit.resolved_options),
        "option_sources": dict(audit.option_sources),
        "drift": {
            "detected": audit.drift.detected,
            "detail": audit.drift.detail,
        },
    }


def _entrypoint_text(text: str) -> str:
    match = re.search(r'(?im)^\s*ENTRYPOINT\s+(\[[^\]]+\]|.+)$', text)
    return match.group(1) if match else ""


def _has_non_root_user(text: str, options: DockerfileOptions) -> bool:
    if not options.non_root:
        return True
    if "USER 1001" in text or "USER nonroot" in text:
        return True
    if options.runtime_image == "distroless" and "gcr.io/distroless" in text:
        return True
    return bool(re.search(r"(?im)^\s*USER\s+\d+", text))


def run_config_verify_checks(audit: ConfigAudit, dockerfile_text: str) -> list[tuple[str, str, str]]:
    """Return (check_name, status, detail) tuples."""
    checks: list[tuple[str, str, str]] = []
    options = audit.resolved_options

    if audit.drift.detected:
        checks.append(("config-drift", "failed", audit.drift.detail))
    else:
        checks.append(("config-drift", "passed", audit.drift.detail))

    if options.include_embedded_sbom:
        if "/usr/share/sbom/spdx.json" in dockerfile_text:
            checks.append(("config-embedded-sbom", "passed", "Dockerfile embeds SPDX SBOM path"))
        else:
            checks.append(
                (
                    "config-embedded-sbom",
                    "failed",
                    "include_embedded_sbom=true but Dockerfile omits /usr/share/sbom/spdx.json",
                )
            )

    if options.non_root:
        if _has_non_root_user(dockerfile_text, options):
            checks.append(("config-non-root", "passed", "non-root USER directive detected"))
        else:
            checks.append(("config-non-root", "failed", "non_root=true but Dockerfile has no unprivileged USER"))

    expected_flags = options.resolved_jvm_flags()
    if expected_flags:
        entrypoint = _entrypoint_text(dockerfile_text)
        missing = [flag for flag in expected_flags if flag not in entrypoint]
        if missing:
            checks.append(
                (
                    "config-jvm-flags",
                    "failed",
                    "missing configured JVM flags in ENTRYPOINT: " + ", ".join(missing),
                )
            )
        else:
            checks.append(("config-jvm-flags", "passed", "configured JVM flags present in ENTRYPOINT"))

    return checks

