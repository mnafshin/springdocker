from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from .commands import (
    cmd_benchmark_analyze,
    cmd_benchmark_compare,
    cmd_benchmark_generate,
    cmd_benchmark_run,
    cmd_configure,
    cmd_dockerfile_generate,
    cmd_doctor,
    cmd_explain,
    cmd_init,
    cmd_inspect,
    cmd_verify,
)
from .config import (
    load_config,
    resolve_benchmark_generate_config,
    resolve_benchmark_run_config,
    resolve_dockerfile_generate_config,
    resolve_doctor_config,
)
from .errors import print_warning
from .plugins import register_command_plugins
from .services import dockerfile_service

# Type alias for dispatch handlers: each receives parsed args and resolved project root.
_Handler = Callable[[argparse.Namespace, Path], int]

# Dispatch key: (command,) for top-level commands, (command, subcommand) for nested ones.
_DispatchKey = tuple[str, ...]

# Nested subcommand attribute names keyed by their parent command name.
_SUBCOMMAND_ATTR: dict[str, str] = {
    "dockerfile": "dockerfile_command",
    "benchmark": "benchmark_command",
}


# Populated by build_parser() when plugin commands are registered.
_PLUGIN_REGISTRATION_WARNINGS: tuple[str, ...] = ()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="springdocker",
        description="CLI for Dockerfile and benchmark workflows in Spring Boot Maven/Gradle projects.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common_options(p: argparse.ArgumentParser, with_build_tool: bool = True) -> None:
        p.add_argument("--project-root", default=".", help="Project root path (default: current directory)")
        if with_build_tool:
            p.add_argument("--build-tool", choices=["maven", "gradle"], default=None,
                           help="Override auto-detected build tool")

    init = sub.add_parser("init", help="Generate starter .springdocker.toml for this project")
    add_common_options(init)
    init.add_argument("--config", default=".springdocker.toml", help="Config file path to create")
    init.add_argument(
        "--profile",
        choices=["quick", "full"],
        default="quick",
        help="Default benchmark run profile to write in the generated config",
    )
    init.add_argument("--print", action="store_true", dest="print_only", help="Print config template to stdout")
    init.add_argument("--force", action="store_true", help="Overwrite existing config file")
    init.add_argument(
        "--interactive",
        action="store_true",
        help="After init, run configure wizard to populate [dockerfile] options",
    )

    configure = sub.add_parser("configure", help="Interactive wizard that writes .springdocker.toml")
    add_common_options(configure)
    configure.add_argument("--config", default=".springdocker.toml", help="Config file path")
    configure.add_argument("--force", action="store_true", help="Overwrite existing [dockerfile] section")
    configure.add_argument(
        "--generate",
        action="store_true",
        help="Run dockerfile generate immediately after writing config",
    )

    doctor = sub.add_parser("doctor", help="Detect project and validate basic prerequisites")
    add_common_options(doctor)

    inspect = sub.add_parser("inspect", help="Inspect project metadata and static compatibility signals")
    add_common_options(inspect)
    inspect.add_argument("--format", choices=["table", "json"], default="table")

    explain = sub.add_parser("explain", help="Explain a Dockerfile")
    add_common_options(explain)
    explain.add_argument("dockerfile", nargs="?", default="Dockerfile.generated")
    explain.add_argument("--format", choices=["table", "json"], default="table")

    verify = sub.add_parser("verify", help="Run verification checks against a Dockerfile and project context")
    add_common_options(verify, with_build_tool=False)
    verify.add_argument("--dockerfile", default="Dockerfile.generated")
    verify.add_argument("--image", default=None, help="Optional built image reference for dive/cosign checks")
    verify.add_argument("--smoke-url", default=None, help="Optional HTTP endpoint for smoke verification")
    verify.add_argument("--format", default="table")
    verify.add_argument("--output", default=None, help="Write verification report to file")

    dockerfile = sub.add_parser("dockerfile", help="Dockerfile operations")
    dockerfile_sub = dockerfile.add_subparsers(dest="dockerfile_command", required=True)
    gen = dockerfile_sub.add_parser("generate", help="Generate Dockerfile via existing wizard")
    add_common_options(gen)
    gen.add_argument("--output", default=None, help="Output Dockerfile path")
    gen.add_argument("--java-version", type=int, default=None, help="Java major version for generated Dockerfile")
    gen.add_argument(
        "--recipe",
        default=None,
        help=(
            "Dockerfile generation recipe preset "
            "(jvm-balanced, spring-aot, native-aot scaffold); "
            "native-aot is experimental and not a production workflow"
        ),
    )
    gen.add_argument(
        "--wizard-arg",
        action="append",
        default=None,
        help="Extra argument forwarded to tools/dockerfile_wizard.py; repeat for multiple args",
    )
    gen.add_argument(
        "--use-legacy-scripts",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Use project scripts instead of internal implementation (or set SPRINGDOCKER_LEGACY_SCRIPTS=1)",
    )

    bench = sub.add_parser("benchmark", help="Benchmark operations")
    bench_sub = bench.add_subparsers(dest="benchmark_command", required=True)

    bench_gen = bench_sub.add_parser("generate", help="Generate benchmark variants for selected build tool")
    add_common_options(bench_gen)
    bench_gen.add_argument("--java-version", type=int, default=None)
    bench_gen.add_argument(
        "--use-legacy-scripts",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Use project scripts instead of internal implementation (or set SPRINGDOCKER_LEGACY_SCRIPTS=1)",
    )

    bench_run = bench_sub.add_parser("run", help="Run benchmark orchestration")
    add_common_options(bench_run)
    bench_run.add_argument("--profile", choices=["quick", "full"], default=None)
    bench_run.add_argument(
        "--config",
        default=".springdocker.toml",
        help="Path to TOML config file relative to project root (default: .springdocker.toml)",
    )
    bench_run.add_argument(
        "--runner-arg",
        action="append",
        default=None,
        help="Extra argument forwarded to benchmarks/common/run_all_benchmarks.py; repeat for multiple args",
    )
    bench_run.add_argument("--cpuset-cpus", default=None, help="Pin benchmark containers to a CPU set")
    bench_run.add_argument("--memory", default=None, help="Limit benchmark containers to a memory amount")
    bench_run.add_argument(
        "--warmup-runs",
        type=int,
        default=None,
        help="Run extra warmup iterations before recording benchmark rows",
    )
    bench_run.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Run standard benchmark scenarios concurrently with up to this many workers",
    )
    bench_run.add_argument(
        "--normalized-runtime",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Apply normalized container runtime flags for reproducible benchmark runs",
    )
    bench_run.add_argument(
        "--use-legacy-scripts",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Use project scripts instead of internal implementation (or set SPRINGDOCKER_LEGACY_SCRIPTS=1)",
    )

    bench_analyze = bench_sub.add_parser("analyze", help="Analyze benchmark CSV")
    add_common_options(bench_analyze, with_build_tool=False)
    bench_analyze.add_argument("raw_csv", help="Path to results raw.csv")
    bench_analyze.add_argument("--format", choices=["table", "json"], default="table")
    bench_analyze.add_argument("--scenario", default=None, help="Filter by scenario id")
    bench_analyze.add_argument("--variant", default=None, help="Filter by variant name")
    bench_analyze.add_argument("--output", default=None, help="Write output to file instead of stdout")
    bench_analyze.add_argument(
        "--fail-on-success-rate-below",
        type=float,
        default=None,
        help="Exit non-zero when any variant success rate is below this percentage (0-100)",
    )
    bench_analyze.add_argument("--baseline", default=None, help="Path to a baseline JSON report")
    bench_analyze.add_argument(
        "--fail-on-regression-above",
        type=float,
        default=None,
        help="Exit non-zero when any tracked metric regresses above this percentage",
    )

    bench_compare = bench_sub.add_parser("compare", help="Compare benchmark variants against a baseline")
    add_common_options(bench_compare, with_build_tool=False)
    bench_compare.add_argument("raw_csv", help="Path to results raw.csv")
    bench_compare.add_argument("--baseline-variant", required=True, help="Variant name to use as the baseline")
    bench_compare.add_argument("--scenario", default=None, help="Filter by scenario id")
    bench_compare.add_argument("--format", choices=["table", "json"], default="table")

    global _PLUGIN_REGISTRATION_WARNINGS
    _PLUGIN_REGISTRATION_WARNINGS = register_command_plugins(sub)
    return parser


def _resolve_dockerfile_config(args: argparse.Namespace, loaded: dict) -> object:
    return resolve_dockerfile_generate_config(
        cli_build_tool=getattr(args, "build_tool", None),
        cli_output=getattr(args, "output", None),
        cli_java_version=getattr(args, "java_version", None),
        cli_recipe=getattr(args, "recipe", None),
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
        cli_wizard_args=getattr(args, "wizard_arg", None),
        cli_use_legacy_scripts=getattr(args, "use_legacy_scripts", None),
        loaded_config=loaded,
    )


def _handle_init(args: argparse.Namespace, project_root: Path) -> int:
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = project_root / config_path
    code = cmd_init(
        project_root=project_root,
        build_tool=args.build_tool,
        config_path=config_path,
        profile=args.profile,
        force=args.force,
        print_only=args.print_only,
    )
    if code != 0 or args.print_only or not args.interactive:
        return code
    return cmd_configure(
        project_root=project_root,
        build_tool=args.build_tool,
        config_path=config_path,
        force=True,
        generate_after=False,
    )


def _handle_configure(args: argparse.Namespace, project_root: Path) -> int:
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = project_root / config_path
    return cmd_configure(
        project_root=project_root,
        build_tool=args.build_tool,
        config_path=config_path,
        force=args.force,
        generate_after=args.generate,
    )


def _handle_doctor(args: argparse.Namespace, project_root: Path) -> int:
    loaded = load_config(project_root / ".springdocker.toml")
    resolved = resolve_doctor_config(cli_build_tool=args.build_tool, loaded_config=loaded)
    return cmd_doctor(project_root, resolved.build_tool)


def _handle_inspect(args: argparse.Namespace, project_root: Path) -> int:
    return cmd_inspect(project_root=project_root, build_tool=args.build_tool, output_format=args.format)


def _handle_explain(args: argparse.Namespace, project_root: Path) -> int:
    return cmd_explain(project_root=project_root, dockerfile_path=args.dockerfile, output_format=args.format)


def _handle_verify(args: argparse.Namespace, project_root: Path) -> int:
    return cmd_verify(
        project_root=project_root,
        dockerfile_path=args.dockerfile,
        image=args.image,
        smoke_url=args.smoke_url,
        output_format=args.format,
        output_path=args.output,
    )


def _handle_dockerfile_generate(args: argparse.Namespace, project_root: Path) -> int:
    loaded = load_config(project_root / ".springdocker.toml")
    resolved = _resolve_dockerfile_config(args, loaded)
    return cmd_dockerfile_generate(project_root=project_root, config=resolved)


def _handle_benchmark_generate(args: argparse.Namespace, project_root: Path) -> int:
    loaded = load_config(project_root / ".springdocker.toml")
    resolved = resolve_benchmark_generate_config(
        cli_build_tool=args.build_tool,
        cli_java_version=args.java_version,
        cli_use_legacy_scripts=args.use_legacy_scripts,
        loaded_config=loaded,
    )
    dockerfile_resolved = _resolve_dockerfile_config(args, loaded)
    must_have_modules = dockerfile_service.parse_must_have_modules(
        project_root,
        dockerfile_resolved.must_have_modules_file,
    )
    return cmd_benchmark_generate(
        project_root=project_root,
        build_tool=resolved.build_tool,
        java_version=resolved.java_version,
        use_legacy_scripts=resolved.use_legacy_scripts,
        must_have_modules=must_have_modules,
        base_image_variants=resolved.base_image_variants,
    )


def _handle_benchmark_run(args: argparse.Namespace, project_root: Path) -> int:
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = project_root / config_path
    loaded = load_config(config_path)
    resolved = resolve_benchmark_run_config(
        cli_build_tool=args.build_tool,
        cli_profile=args.profile,
        cli_runner_args=args.runner_arg,
        cli_cpuset_cpus=args.cpuset_cpus,
        cli_memory_limit=args.memory,
        cli_warmup_runs=args.warmup_runs,
        cli_max_workers=args.max_workers,
        cli_normalized_runtime=args.normalized_runtime,
        cli_use_legacy_scripts=args.use_legacy_scripts,
        loaded_config=loaded,
    )
    return cmd_benchmark_run(
        project_root=project_root,
        build_tool=resolved.build_tool,
        profile=resolved.profile,
        extra_args=resolved.runner_args,
        cpuset_cpus=resolved.cpuset_cpus,
        memory_limit=resolved.memory_limit,
        warmup_runs=resolved.warmup_runs,
        max_workers=resolved.max_workers,
        normalized_runtime=resolved.normalized_runtime,
        use_legacy_scripts=resolved.use_legacy_scripts,
    )


def _handle_benchmark_analyze(args: argparse.Namespace, project_root: Path) -> int:
    return cmd_benchmark_analyze(
        project_root=project_root,
        raw_csv=args.raw_csv,
        output_format=args.format,
        scenario=args.scenario,
        variant=args.variant,
        output_path=args.output,
        fail_on_success_rate_below=args.fail_on_success_rate_below,
        baseline_path=args.baseline,
        fail_on_regression_above=args.fail_on_regression_above,
    )


def _handle_benchmark_compare(args: argparse.Namespace, project_root: Path) -> int:
    return cmd_benchmark_compare(
        project_root=project_root,
        raw_csv=args.raw_csv,
        baseline_variant=args.baseline_variant,
        output_format=args.format,
        scenario=args.scenario,
    )


# Registry mapping dispatch keys to handler functions.
# Top-level commands use a one-element key; nested commands use (parent, subcommand).
# To add a new command: register a parser in build_parser() and add an entry here.
_DISPATCH: dict[_DispatchKey, _Handler] = {
    ("init",): _handle_init,
    ("configure",): _handle_configure,
    ("doctor",): _handle_doctor,
    ("inspect",): _handle_inspect,
    ("explain",): _handle_explain,
    ("verify",): _handle_verify,
    ("dockerfile", "generate"): _handle_dockerfile_generate,
    ("benchmark", "generate"): _handle_benchmark_generate,
    ("benchmark", "run"): _handle_benchmark_run,
    ("benchmark", "analyze"): _handle_benchmark_analyze,
    ("benchmark", "compare"): _handle_benchmark_compare,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()
    for warning in _PLUGIN_REGISTRATION_WARNINGS:
        print_warning(warning)

    plugin_handler = cast(Any, getattr(args, "_plugin_handler", None))
    if plugin_handler is not None:
        if not callable(plugin_handler):
            parser.error("invalid plugin handler")
            return 2
        return cast(int, plugin_handler(args, project_root))

    sub_attr = _SUBCOMMAND_ATTR.get(args.command)
    key: _DispatchKey = (args.command, getattr(args, sub_attr)) if sub_attr else (args.command,)

    handler = _DISPATCH.get(key)
    if handler is None:
        parser.error("unknown command")
        return 2
    return handler(args, project_root)


if __name__ == "__main__":
    raise SystemExit(main())
