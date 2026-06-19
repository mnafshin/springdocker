"""Serialize DockerfileOptions into .springdocker.toml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from springdocker.dockerfile import DockerfileOptions

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


def _toml_bool(value: bool) -> str:
    return "true" if value else "false"


def _toml_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_str_list(values: tuple[str, ...]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(_toml_str(item) for item in values) + "]"


def dockerfile_options_to_table(options: DockerfileOptions, *, profile: str | None = None) -> dict[str, Any]:
    table: dict[str, Any] = {
        "output": "Dockerfile.generated",
        "java_version": options.java_version,
        "recipe": options.recipe,
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
    }
    if profile is not None:
        table["profile"] = profile
    if options.jvm_flags:
        table["jvm_flags"] = list(options.jvm_flags)
    if options.jlink_baseline_modules != ():
        table["jlink_baseline_modules"] = list(options.jlink_baseline_modules)
    return table


def render_dockerfile_section(table: dict[str, Any]) -> str:
    lines = ["[dockerfile]"]
    key_order = [
        "profile",
        "output",
        "java_version",
        "recipe",
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
        "jlink_baseline_modules",
        "must_have_modules_file",
    ]
    for key in key_order:
        if key not in table:
            continue
        value = table[key]
        if isinstance(value, bool):
            lines.append(f"{key} = {_toml_bool(value)}")
        elif isinstance(value, int):
            lines.append(f"{key} = {value}")
        elif isinstance(value, str):
            lines.append(f"{key} = {_toml_str(value)}")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{key} = []")
            elif all(isinstance(item, str) for item in value):
                lines.append(f"{key} = {_toml_str_list(tuple(value))}")
            else:
                raise ValueError(f"unsupported list value for dockerfile.{key}")
        else:
            raise ValueError(f"unsupported value for dockerfile.{key}: {type(value)!r}")
    return "\n".join(lines) + "\n"


def merge_dockerfile_section(config_path: Path, table: dict[str, Any]) -> None:
    """Replace or insert the [dockerfile] section; preserve other sections."""
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    dockerfile_block = render_dockerfile_section(table)

    if "[dockerfile]" not in existing:
        merged = existing.rstrip() + ("\n\n" if existing.strip() else "") + dockerfile_block
        config_path.write_text(merged, encoding="utf-8")
        return

    lines = existing.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.strip() == "[dockerfile]")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = index
            break
    merged_lines = lines[:start] + [dockerfile_block] + lines[end:]
    config_path.write_text("".join(merged_lines), encoding="utf-8")


def load_existing_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Config root must be a TOML table")
    return data
