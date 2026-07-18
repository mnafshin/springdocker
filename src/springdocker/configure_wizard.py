"""Interactive and non-interactive writers for .springdocker.toml (config SSOT)."""

from __future__ import annotations

from pathlib import Path

from springdocker.config import HEALTHCHECK_AUTO, DockerfileGenerateConfig, write_default_config
from springdocker.config_serializer import dockerfile_options_to_table, merge_dockerfile_section
from springdocker.dockerfile import DockerfileOptions
from springdocker.dockerfile_profiles import (
    PROFILE_NAMES,
    apply_profile_for_java,
    default_jvm_flags_for_display,
    profile_description,
)
from springdocker.java_features import JEP483_MIN_JAVA, MIN_JAVA_VERSION, jep483_supported
from springdocker.project_detect import inspect_project_details

# Profiles safe for non-interactive setup (excludes "custom", which needs the wizard).
NONINTERACTIVE_PROFILES: tuple[str, ...] = tuple(name for name in PROFILE_NAMES if name != "custom")


def ask_choice(prompt: str, options: list[str], default_index: int) -> str:
    print(f"\n{prompt}")
    for index, option in enumerate(options, start=1):
        marker = " (default)" if index == default_index else ""
        print(f"  {index}) {option}{marker}")
    raw = input("> ").strip()
    if not raw:
        return options[default_index - 1]
    if raw.isdigit() and 1 <= int(raw) <= len(options):
        return options[int(raw) - 1]
    print("Invalid choice, using default.")
    return options[default_index - 1]


def ask_bool(prompt: str, default: bool) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    raw = input(f"\n{prompt} {suffix} ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


def _startup_optimization_choice(java_version: int) -> tuple[bool, bool]:
    if jep483_supported(java_version):
        choice = ask_choice(
            "Startup optimization:",
            ["none", "AppCDS", "JEP 483 AOT cache"],
            default_index=1,
        )
    else:
        choice = ask_choice(
            f"Startup optimization (JEP 483 requires Java {JEP483_MIN_JAVA}+):",
            ["none", "AppCDS"],
            default_index=1,
        )
    if choice == "AppCDS":
        return True, False
    if choice == "JEP 483 AOT cache":
        return False, True
    return False, False


def _edit_jvm_flags(defaults: tuple[str, ...]) -> tuple[str, ...]:
    print("\nRecommended JVM flags:")
    for flag in defaults:
        print(f"  - {flag}")
    if not ask_bool("Use these JVM flags?", True):
        if ask_bool("Disable tuned JVM flags entirely?", False):
            return ()
        print("Enter flags one per line; blank line to finish:")
        flags: list[str] = []
        while True:
            line = input("> ").strip()
            if not line:
                break
            flags.append(line)
        return tuple(flags)
    return defaults


def _write_dockerfile_config(
    config_path: Path,
    options: DockerfileOptions,
    *,
    profile: str,
    build_tool: str,
    output: str = "Dockerfile.generated",
) -> DockerfileGenerateConfig:
    if not config_path.exists():
        write_default_config(config_path, build_tool=build_tool, profile="quick", force=False)

    table = dockerfile_options_to_table(options, profile=profile)
    table["output"] = output
    merge_dockerfile_section(config_path, table)

    return DockerfileGenerateConfig(
        build_tool=build_tool,
        output=output,
        java_version=options.java_version,
        recipe=options.recipe,
        profile=profile,
        must_have_modules_file=None,
        jlink_baseline_modules=options.jlink_baseline_modules,
        runtime_image=options.runtime_image,
        use_buildkit_cache=options.use_buildkit_cache,
        use_jlink=options.use_jlink,
        use_layered_jar=options.use_layered_jar,
        non_root=options.non_root,
        platform_aware=options.platform_aware,
        enable_appcds=options.enable_appcds,
        enable_jep483_aot_cache=options.enable_jep483_aot_cache,
        include_oci_labels=options.include_oci_labels,
        include_stopsignal=options.include_stopsignal,
        include_embedded_sbom=options.include_embedded_sbom,
        include_reproducible_controls=options.include_reproducible_controls,
        pin_digests=options.pin_digests,
        tuned_jvm_flags=options.tuned_jvm_flags,
        jvm_flags=options.jvm_flags,
        healthcheck_path=HEALTHCHECK_AUTO,
    )


def apply_profile_to_config(
    project_root: Path,
    config_path: Path,
    *,
    profile: str = "production-balanced",
    build_tool: str | None = None,
    force: bool = False,
    output: str = "Dockerfile.generated",
) -> tuple[DockerfileGenerateConfig, str | None]:
    """Apply a named Dockerfile profile without prompting (used by ``setup``)."""
    if profile not in NONINTERACTIVE_PROFILES:
        supported = ", ".join(NONINTERACTIVE_PROFILES)
        raise ValueError(
            f"profile {profile!r} requires interactive configure "
            f"(use one of: {supported}, or pass --interactive)"
        )

    info = inspect_project_details(project_root, explicit_build_tool=build_tool)
    if config_path.exists() and not force:
        raise FileExistsError(f"Config already exists: {config_path}")

    java_version = info.java_version or MIN_JAVA_VERSION
    base = DockerfileOptions(build_tool=info.build_tool, java_version=java_version)
    options, remap_warning = apply_profile_for_java(base, profile, java_version)
    resolved = _write_dockerfile_config(
        config_path,
        options,
        profile=profile,
        build_tool=info.build_tool,
        output=output,
    )
    return resolved, remap_warning


def run_configure_wizard(
    project_root: Path,
    config_path: Path,
    *,
    build_tool: str | None = None,
    force: bool = False,
    generate_after: bool = False,
) -> DockerfileGenerateConfig:
    info = inspect_project_details(project_root, explicit_build_tool=build_tool)
    print("Project context:")
    print(f"  build_tool: {info.build_tool}")
    print(f"  java_version: {info.java_version if info.java_version is not None else '-'}")
    print(f"  spring_boot_version: {info.spring_boot_version or '-'}")
    print(f"  spring_markers: {'yes' if info.has_spring_markers else 'no'}")

    profile_labels = [f"{name} — {profile_description(name)}" for name in PROFILE_NAMES if name != "custom"]
    profile_labels.append(f"custom — {profile_description('custom')}")
    selected_label = ask_choice("Choose Dockerfile profile:", profile_labels, default_index=1)
    profile = selected_label.split(" — ", 1)[0]

    java_version = info.java_version or MIN_JAVA_VERSION
    if profile == "custom":
        java_raw = input(f"\nJava major version [{java_version}]: ").strip()
        if java_raw.isdigit():
            java_version = int(java_raw)
        runtime_image = ask_choice(
            "Runtime base image:",
            ["distroless", "debian-slim", "alpine", "ubuntu", "temurin"],
            default_index=1,
        )
        use_jlink = ask_bool("Use jlink custom runtime?", runtime_image != "temurin")
        enable_appcds, enable_jep483 = _startup_optimization_choice(java_version)
        if enable_jep483 and not use_jlink:
            print("Note: JEP 483 requires jlink; enabling jlink.")
            use_jlink = True
        recipe = ask_choice("Recipe:", ["jvm-balanced", "spring-aot"], default_index=1)
        use_buildkit_cache = ask_bool("Use BuildKit dependency cache mount?", True)
        use_layered_jar = ask_bool("Use layered JAR extraction?", True)
        non_root = ask_bool("Run container as non-root user?", True)
        include_sbom = ask_bool("Embed SBOM in image?", True)
        pin_digests = ask_bool("Pin known base-image digests?", True)
        jvm_flags = _edit_jvm_flags(default_jvm_flags_for_display())
        tuned_jvm_flags = bool(jvm_flags)
        options = DockerfileOptions(
            build_tool=info.build_tool,
            recipe=recipe,
            java_version=java_version,
            runtime_image=runtime_image,
            use_buildkit_cache=use_buildkit_cache,
            use_jlink=use_jlink,
            use_layered_jar=use_layered_jar,
            non_root=non_root,
            enable_appcds=enable_appcds,
            enable_jep483_aot_cache=enable_jep483,
            include_embedded_sbom=include_sbom,
            pin_digests=pin_digests,
            tuned_jvm_flags=tuned_jvm_flags,
            jvm_flags=jvm_flags if jvm_flags != default_jvm_flags_for_display() else (),
        )
    else:
        base = DockerfileOptions(build_tool=info.build_tool, java_version=java_version)
        options, remap_warning = apply_profile_for_java(base, profile, java_version)
        if remap_warning:
            print(f"Warning: {remap_warning}")

    print("\nSummary:")
    print(f"  profile: {profile}")
    print(f"  runtime: {options.runtime_image}")
    print(f"  recipe: {options.recipe}")
    print(f"  jlink: {options.use_jlink}")
    print(f"  AppCDS: {options.enable_appcds}")
    print(f"  JEP 483 AOT: {options.enable_jep483_aot_cache}")
    print(f"  SBOM: {options.include_embedded_sbom}")
    print(f"  digest pins: {options.pin_digests}")
    print(f"  JVM flags: {', '.join(options.resolved_jvm_flags()) or '(none)'}")

    if not ask_bool("\nWrite .springdocker.toml?", True):
        raise SystemExit("configure cancelled")

    resolved = _write_dockerfile_config(
        config_path,
        options,
        profile=profile,
        build_tool=info.build_tool,
    )

    print(f"\nwrote config: {config_path}")
    print("next: springdocker dockerfile generate")
    return resolved
