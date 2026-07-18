from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import cast

from .benchmarks.generate import generate_benchmark_assets
from .benchmarks.runner import run_benchmarks
from .ci_workflow import write_dockerfile_ssot_workflow
from .config import DockerfileGenerateConfig, load_config, resolve_dockerfile_generate_config
from .configure_wizard import apply_profile_to_config, run_configure_wizard
from .errors import EXIT_FAILURE, EXIT_OK, EXIT_USAGE, print_error, print_warning
from .plugins import render_verify_with_plugins
from .project_detect import inspect_project
from .regression import format_regression_json, format_regression_table
from .services import benchmark_service, dockerfile_service, project_service
from .services.verify_service import (
    VerifyContext,
    render_verify_json,
    render_verify_junit,
    render_verify_sarif,
    render_verify_table,
    run_verification,
)


def run_checked(command: list[str], cwd: Path) -> int:
    print("$ " + " ".join(command))
    completed = subprocess.run(command, cwd=cwd)
    return completed.returncode


def cmd_doctor(project_root: Path, build_tool: str | None) -> int:
    try:
        info = project_service.load_project_info(project_root, build_tool)
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE

    print(f"project_root: {info.root}")
    print(f"build_tool: {info.build_tool}")
    print(f"spring_markers: {'yes' if info.has_spring_markers else 'no'}")
    if not info.has_spring_markers:
        print_warning("Spring Boot markers were not found; continue only if this is intentional.")
    return EXIT_OK


def _render_inspect_table(info) -> str:
    lines = [
        "| Field | Value |",
        "|---|---|",
        f"| Project root | {info.root} |",
        f"| Build tool | {info.build_tool} |",
        f"| Spring markers | {'yes' if info.has_spring_markers else 'no'} |",
        f"| Java version | {info.java_version if info.java_version is not None else '-'} |",
        f"| Spring Boot version | {info.spring_boot_version or '-'} |",
        f"| Config exists | {'yes' if info.config_exists else 'no'} |",
        f"| Generated Dockerfiles | {', '.join(info.generated_dockerfiles) or '-'} |",
        f"| Direct dependencies | {', '.join(info.direct_dependencies) or '-'} |",
        f"| Reflection hits | {len(info.reflection_hits)} |",
        f"| Runtime compatibility | {info.runtime_compatibility} |",
        f"| Layout | {info.layout} |",
        f"| Modules | {', '.join(info.modules) or '-'} |",
        f"| Spring Boot modules | {', '.join(info.spring_boot_modules) or '-'} |",
        f"| Recommendations | {'; '.join(info.recommendations) or '-'} |",
    ]
    return "\n".join(lines)


def cmd_inspect(project_root: Path, build_tool: str | None, output_format: str) -> int:
    try:
        info = project_service.load_project_details(project_root, build_tool)
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE

    payload = {
        "project_root": str(info.root),
        "build_tool": info.build_tool,
        "has_spring_markers": info.has_spring_markers,
        "java_version": info.java_version,
        "spring_boot_version": info.spring_boot_version,
        "direct_dependencies": list(info.direct_dependencies),
        "config_exists": info.config_exists,
        "generated_dockerfiles": list(info.generated_dockerfiles),
        "reflection_hits": list(info.reflection_hits),
        "runtime_compatibility": info.runtime_compatibility,
        "recommendations": list(info.recommendations),
        "layout": info.layout,
        "modules": list(info.modules),
        "spring_boot_modules": list(info.spring_boot_modules),
    }
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_render_inspect_table(info))
    return EXIT_OK


def _render_explain_table(payload: dict[str, object]) -> str:
    features = cast(list[dict[str, object]], payload.get("features", []))
    feature_names = ", ".join(
        str(feature["name"]) for feature in features if feature.get("enabled") and "name" in feature
    )
    notes = cast(list[str], payload.get("notes", []))
    jlink_modules = cast(dict[str, list[str]], payload.get("jlink_modules", {}))
    baseline_modules = ", ".join(jlink_modules.get("baseline", [])) or "-"
    curated_modules = ", ".join(jlink_modules.get("curated", [])) or "-"
    lines = [
        "| Field | Value |",
        "|---|---|",
        f"| Source | {payload.get('source', '-')} |",
        f"| Build tool | {payload.get('build_tool') or '-'} |",
        f"| Java version | {payload.get('java_version') if payload.get('java_version') is not None else '-'} |",
        f"| Stage count | {payload.get('stage_count', '-')} |",
        f"| Features | {feature_names or '-'} |",
        f"| Jlink baseline modules | {baseline_modules} |",
        f"| Curated must-have modules | {curated_modules} |",
        f"| Summary | {payload.get('summary', '-')} |",
        f"| Notes | {'; '.join(notes) if notes else '-'} |",
    ]
    config_aware = payload.get("config_aware")
    if isinstance(config_aware, dict):
        lines.extend(
            [
                f"| Config present | {'yes' if config_aware.get('config_present') else 'no'} |",
            ]
        )
        drift = config_aware.get("drift")
        if isinstance(drift, dict):
            drift_label = "yes" if drift.get("detected") else "no"
            lines.append(f"| Config drift | {drift_label} ({drift.get('detail', '-')}) |")
        resolved_options = config_aware.get("resolved_options")
        if isinstance(resolved_options, dict):
            lines.append(f"| Config runtime image | {resolved_options.get('runtime_image', '-')} |")
    return "\n".join(lines)


def cmd_benchmark_compare(
    project_root: Path,
    raw_csv: str,
    baseline_variant: str,
    output_format: str,
    scenario: str | None,
) -> int:
    try:
        benchmark_service.require_benchmark_dependencies()
        rendered = benchmark_service.render_comparison(
            project_root=project_root,
            raw_csv=raw_csv,
            baseline_variant=baseline_variant,
            output_format=output_format,
            scenario=scenario,
        )
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE

    print(rendered)
    return EXIT_OK


def cmd_explain(
    project_root: Path,
    dockerfile_path: str,
    output_format: str,
    *,
    config_aware: bool = False,
    build_tool: str | None = None,
) -> int:
    try:
        payload = dockerfile_service.explain_dockerfile(
            project_root,
            dockerfile_path,
            config_aware=config_aware,
            build_tool=build_tool,
        )
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE

    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_render_explain_table(payload))
    return EXIT_OK


def cmd_verify(
    project_root: Path,
    dockerfile_path: str,
    image: str | None,
    smoke_url: str | None,
    output_format: str,
    output_path: str | None,
    *,
    check_config_drift: bool = False,
    build_tool: str | None = None,
    trivy_scan_project_root: bool = False,
) -> int:
    path = Path(dockerfile_path)
    if not path.is_absolute():
        path = project_root / path
    if not path.exists():
        print_error(f"missing Dockerfile: {path}")
        return EXIT_USAGE

    outcome = run_verification(
        VerifyContext(
            project_root=project_root,
            dockerfile_path=path,
            image=image,
            smoke_url=smoke_url,
            check_config_drift=check_config_drift,
            build_tool=build_tool,
            trivy_scan_project_root=trivy_scan_project_root,
        )
    )

    if output_format == "json":
        rendered = render_verify_json(outcome)
    elif output_format == "junit":
        rendered = render_verify_junit(outcome)
    elif output_format == "sarif":
        rendered = render_verify_sarif(outcome)
    elif output_format == "table":
        rendered = render_verify_table(outcome)
    else:
        plugin_render = render_verify_with_plugins(output_format, outcome)
        for warning in plugin_render.warnings:
            print_warning(warning)
        if plugin_render.handled and plugin_render.rendered is not None:
            rendered = plugin_render.rendered
        elif plugin_render.handled:
            print_error(f"verify format '{output_format}' was handled by plugin but produced no output")
            return EXIT_USAGE
        else:
            print_error(f"unknown verify format: {output_format}")
            return EXIT_USAGE

    if output_path is not None:
        destination = Path(output_path)
        if not destination.is_absolute():
            destination = project_root / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered + ("\n" if not rendered.endswith("\n") else ""), encoding="utf-8")
        print(f"wrote verification report: {destination}")
    else:
        print(rendered)
    return EXIT_FAILURE if outcome.failed else EXIT_OK


def cmd_init(
    project_root: Path,
    build_tool: str | None,
    config_path: Path,
    profile: str,
    force: bool,
    print_only: bool,
) -> int:
    try:
        result = project_service.prepare_default_config(
            project_root=project_root,
            build_tool=build_tool,
            config_path=config_path,
            profile=profile,
            force=force,
            print_only=print_only,
        )
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE
    except FileExistsError as exc:
        print_error(str(exc))
        print("hint: rerun with --force to overwrite", file=sys.stderr)
        return EXIT_USAGE

    if result.rendered is not None:
        print(result.rendered)
        return EXIT_OK

    print(f"wrote config: {config_path}")
    print("next: springdocker setup   # or: springdocker dockerfile generate")
    return EXIT_OK


def _print_setup_next_steps(
    config_path: Path,
    dockerfile_output: str,
    *,
    verified: bool,
    ci_workflow: Path | None = None,
) -> None:
    print()
    print("next:")
    if ci_workflow is not None:
        print(f"  1. Review {config_path.name}, {dockerfile_output}, and {ci_workflow}")
        print("  2. Commit and push — the Dockerfile SSOT workflow gates PRs")
    else:
        print(f"  1. Review {config_path.name} and {dockerfile_output}")
        if not verified:
            print(
                "  2. springdocker verify --dockerfile "
                f"{dockerfile_output} --check-config-drift"
            )
            print("  3. springdocker setup --ci-only   # write GitHub Actions workflow")
            print("  4. Commit the files")
        else:
            print("  2. springdocker setup --ci-only   # write GitHub Actions workflow")
            print("  3. Commit the files")
    print("  Tip: springdocker configure --force   # change strategy interactively")


def _ensure_placeholder_sbom(project_root: Path) -> None:
    """Write a minimal SPDX stub so verify can pass after first-time setup."""
    sbom_path = project_root / "sbom.spdx.json"
    if sbom_path.exists():
        return
    payload = {
        "spdxVersion": "SPDX-2.3",
        "name": "springdocker-setup-placeholder",
        "comment": "Placeholder SPDX document created by springdocker setup --verify; replace with a real SBOM.",
    }
    sbom_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print_warning(f"wrote placeholder SBOM for verify: {sbom_path}")


def _write_setup_ci_workflow(
    project_root: Path,
    *,
    dockerfile_output: str,
    build_tool: str | None,
    force: bool,
) -> Path | None:
    try:
        path = write_dockerfile_ssot_workflow(
            project_root,
            dockerfile=dockerfile_output,
            build_tool=build_tool,
            force=force,
        )
    except FileExistsError as exc:
        print_error(str(exc))
        print("hint: rerun with --force to overwrite the workflow", file=sys.stderr)
        return None
    print(f"wrote workflow: {path}")
    return path


def cmd_setup(
    project_root: Path,
    build_tool: str | None,
    config_path: Path,
    *,
    profile: str = "production-balanced",
    force: bool = False,
    interactive: bool = False,
    verify: bool = False,
    output: str | None = None,
    ci: bool = False,
    ci_only: bool = False,
) -> int:
    """One-shot onboarding: detect project, write config, generate Dockerfile."""
    dockerfile_output = output or "Dockerfile.generated"
    ci_workflow: Path | None = None

    if ci_only:
        ci_workflow = _write_setup_ci_workflow(
            project_root,
            dockerfile_output=dockerfile_output,
            build_tool=build_tool,
            force=force,
        )
        if ci_workflow is None:
            return EXIT_USAGE
        print()
        print("next: commit the workflow, then open a PR to confirm the SSOT gate")
        return EXIT_OK

    doctor_code = cmd_doctor(project_root, build_tool)
    if doctor_code != EXIT_OK:
        return doctor_code

    if interactive:
        if config_path.exists() and not force:
            print_error(f"Config already exists: {config_path}")
            print("hint: rerun with --force to overwrite the [dockerfile] section", file=sys.stderr)
            return EXIT_USAGE
        configure_code = cmd_configure(
            project_root=project_root,
            build_tool=build_tool,
            config_path=config_path,
            force=True,
            generate_after=True,
        )
        if configure_code != EXIT_OK:
            return configure_code
    else:
        try:
            resolved, remap_warning = apply_profile_to_config(
                project_root,
                config_path,
                profile=profile,
                build_tool=build_tool,
                force=force,
                output=dockerfile_output,
            )
        except FileExistsError as exc:
            print_error(str(exc))
            print("hint: rerun with --force to overwrite the [dockerfile] section", file=sys.stderr)
            print("hint: or springdocker setup --ci-only to write only the GitHub workflow", file=sys.stderr)
            return EXIT_USAGE
        except ValueError as exc:
            print_error(str(exc))
            return EXIT_USAGE

        if remap_warning:
            print_warning(remap_warning)
        print(f"wrote config: {config_path} (profile={profile})")

        if output is not None:
            resolved = replace(resolved, output=output)
        generate_code = cmd_dockerfile_generate(project_root, resolved)
        if generate_code != EXIT_OK:
            return generate_code

    verified = False
    if verify:
        _ensure_placeholder_sbom(project_root)
        verify_code = cmd_verify(
            project_root=project_root,
            dockerfile_path=dockerfile_output,
            image=None,
            smoke_url=None,
            output_format="table",
            output_path=None,
            check_config_drift=True,
            build_tool=build_tool,
            trivy_scan_project_root=False,
        )
        if verify_code != EXIT_OK:
            return verify_code
        verified = True

    if ci:
        ci_workflow = _write_setup_ci_workflow(
            project_root,
            dockerfile_output=dockerfile_output,
            build_tool=build_tool,
            force=force,
        )
        if ci_workflow is None:
            return EXIT_USAGE

    _print_setup_next_steps(
        config_path,
        dockerfile_output,
        verified=verified,
        ci_workflow=ci_workflow,
    )
    return EXIT_OK


LEGACY_BENCHMARK_SCRIPTS_REMOVAL_VERSION = "2.0.0"


def _legacy_benchmark_scripts_warning() -> str:
    return (
        "benchmark legacy scripts (--use-legacy-scripts, SPRINGDOCKER_LEGACY_SCRIPTS, "
        "or [benchmark].legacy_scripts in .springdocker.toml) are deprecated and will be "
        f"removed in v{LEGACY_BENCHMARK_SCRIPTS_REMOVAL_VERSION}; "
        "use the internal benchmark implementation (default since 1.0.x)"
    )


def _use_legacy_scripts(explicit: bool) -> bool:
    if explicit:
        return True
    return os.environ.get("SPRINGDOCKER_LEGACY_SCRIPTS", "").lower() in {"1", "true", "yes", "on"}


def _warn_legacy_benchmark_scripts() -> None:
    print_warning(_legacy_benchmark_scripts_warning())


def cmd_configure(
    project_root: Path,
    build_tool: str | None,
    config_path: Path,
    force: bool,
    generate_after: bool,
) -> int:
    try:
        inspect_project(project_root, build_tool)
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE

    if config_path.exists() and not force:
        print_error(f"Config already exists: {config_path}")
        print("hint: rerun with --force to overwrite the [dockerfile] section", file=sys.stderr)
        return EXIT_USAGE

    try:
        run_configure_wizard(
            project_root=project_root,
            config_path=config_path,
            build_tool=build_tool,
            force=force,
            generate_after=generate_after,
        )
    except SystemExit:
        return EXIT_USAGE
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE

    if generate_after:
        loaded_config = load_config(config_path) if config_path.exists() else {}
        resolved = resolve_dockerfile_generate_config(
            cli_build_tool=build_tool,
            cli_output=None,
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
        )
        return cmd_dockerfile_generate(project_root, resolved)

    return EXIT_OK


def cmd_dockerfile_generate(
    project_root: Path,
    config: DockerfileGenerateConfig,
) -> int:
    try:
        info = inspect_project(project_root, config.build_tool)
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE

    try:
        generated = dockerfile_service.generate_dockerfile_from_config(
            project_root=project_root,
            config=config,
            build_tool=info.build_tool,
        )
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE
    for warning in generated.plugin_warnings:
        print_warning(warning)
    print(f"wrote dockerfile: {generated.path}")
    return EXIT_OK


def cmd_benchmark_generate(
    project_root: Path,
    build_tool: str | None,
    java_version: int,
    use_legacy_scripts: bool,
    must_have_modules: tuple[str, ...] = (),
    base_image_variants: tuple[str, ...] | None = None,
    dockerfile_config: DockerfileGenerateConfig | None = None,
) -> int:
    try:
        benchmark_service.require_benchmark_dependencies()
        info = inspect_project(project_root, build_tool)
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE

    if _use_legacy_scripts(use_legacy_scripts):
        _warn_legacy_benchmark_scripts()
        script = project_root / "benchmarks" / "setup_benchmark_folders.py"
        if not script.exists():
            print_error(f"missing script: {script}")
            return EXIT_USAGE

        return run_checked(
            [
                "python3",
                str(script),
                "--build-tool",
                info.build_tool,
                "--java-version",
                str(java_version),
            ],
            project_root,
        )

    recipe_config = (
        replace(dockerfile_config, java_version=java_version) if dockerfile_config is not None else None
    )
    generate_benchmark_assets(
        project_root=project_root,
        build_tool=info.build_tool,
        java_version=java_version,
        must_have_modules=must_have_modules,
        base_image_variants=base_image_variants,
        dockerfile_config=recipe_config,
    )
    print("generated benchmark scenarios")
    return EXIT_OK


def cmd_benchmark_run(
    project_root: Path,
    build_tool: str | None,
    profile: str,
    extra_args: list[str],
    cpuset_cpus: str | None,
    memory_limit: str | None,
    warmup_runs: int,
    normalized_runtime: bool,
    use_legacy_scripts: bool,
    max_workers: int = 1,
) -> int:
    try:
        benchmark_service.require_benchmark_dependencies()
        info = inspect_project(project_root, build_tool)
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE

    try:
        benchmark_service.validate_reproducibility_with_legacy(
            use_legacy_scripts=use_legacy_scripts,
            cpuset_cpus=cpuset_cpus,
            memory_limit=memory_limit,
            warmup_runs=warmup_runs,
            max_workers=max_workers,
            normalized_runtime=normalized_runtime,
        )
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE

    if _use_legacy_scripts(use_legacy_scripts):
        _warn_legacy_benchmark_scripts()
        script = project_root / "benchmarks" / "common" / "run_all_benchmarks.py"
        if not script.exists():
            print_error(f"missing script: {script}")
            return EXIT_USAGE

        cmd = [
            "python3",
            str(script),
            "--profile",
            profile,
            "--build-tool",
            info.build_tool,
        ]
        cmd.extend(extra_args)
        return run_checked(cmd, project_root)

    return run_benchmarks(
        project_root=project_root,
        build_tool=info.build_tool,
        profile=profile,
        extra_args=extra_args,
        cpuset_cpus=cpuset_cpus,
        memory_limit=memory_limit,
        warmup_runs=warmup_runs,
        max_workers=max_workers,
        normalized_runtime=normalized_runtime,
    )


def cmd_benchmark_analyze(
    project_root: Path,
    raw_csv: str,
    output_format: str,
    scenario: str | None,
    variant: str | None,
    output_path: str | None,
    fail_on_success_rate_below: float | None,
    baseline_path: str | None,
    fail_on_regression_above: float | None,
) -> int:
    try:
        benchmark_service.require_benchmark_dependencies()
        outcome = benchmark_service.analyze_csv(
            project_root=project_root,
            raw_csv=raw_csv,
            output_format=output_format,
            scenario=scenario,
            variant=variant,
            output_path=output_path,
            fail_on_success_rate_below=fail_on_success_rate_below,
            baseline_path=baseline_path,
            fail_on_regression_above=fail_on_regression_above,
        )
    except ValueError as exc:
        print_error(str(exc))
        return EXIT_USAGE

    if outcome.rendered == "No rows matched the provided filters.":
        print(outcome.rendered)
        return EXIT_OK

    if outcome.output_destination is not None:
        destination = outcome.output_destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(outcome.rendered + "\n", encoding="utf-8")
        print(f"wrote analysis: {destination}")
    else:
        print(outcome.rendered)

    if outcome.success_rate_violations:
        for violation in outcome.success_rate_violations:
            print_error(violation)
        return EXIT_FAILURE

    if outcome.baseline_missing is not None:
        print_warning(f"baseline report not found; skipping regression check: {outcome.baseline_missing}")
        return EXIT_OK

    if outcome.regression_violations:
        rendered_violations = (
            format_regression_json(list(outcome.regression_violations))
            if output_format == "json"
            else format_regression_table(list(outcome.regression_violations))
        )
        print(rendered_violations)
        print_error(
            f"regressions above {outcome.regression_threshold_pct:.1f}% detected against {outcome.baseline_path_used}"
        )
        return EXIT_FAILURE

    return EXIT_OK
