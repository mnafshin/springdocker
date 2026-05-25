from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from springdocker.runtime_images import parse_base_image_variants

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - exercised on Python < 3.11
    import tomli as tomllib


@dataclass(frozen=True)
class DoctorConfig:
    build_tool: str | None


@dataclass(frozen=True)
class DockerfileGenerateConfig:
    build_tool: str | None
    output: str
    java_version: int
    recipe: str
    must_have_modules_file: str | None
    wizard_args: list[str]
    use_legacy_scripts: bool


@dataclass(frozen=True)
class BenchmarkGenerateConfig:
    build_tool: str | None
    java_version: int
    use_legacy_scripts: bool
    base_image_variants: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkRunConfig:
    build_tool: str | None
    profile: str
    runner_args: list[str]
    cpuset_cpus: str | None
    memory_limit: str | None
    warmup_runs: int
    max_workers: int
    normalized_runtime: bool
    use_legacy_scripts: bool


def render_default_config(build_tool: str, profile: str = "quick") -> str:
    """Render starter .springdocker.toml content."""
    if profile not in {"quick", "full"}:
        raise ValueError("benchmark profile must be 'quick' or 'full'")
    return (
        "# springdocker project configuration\n"
        "# Precedence: CLI flags > this file > internal defaults\n\n"
        "[project]\n"
        f'build_tool = "{build_tool}"\n\n'
        "[doctor]\n"
        f'build_tool = "{build_tool}"\n\n'
        "[dockerfile]\n"
        'output = "Dockerfile.generated"\n'
        "java_version = 25\n"
        'recipe = "jvm-balanced"\n'
        '# must_have_modules_file = "must-have.txt"\n'
        "legacy_scripts = false\n"
        "wizard_args = []\n\n"
        "[benchmark.generate]\n"
        "java_version = 25\n"
        "legacy_scripts = false\n\n"
        "[benchmark.generate.base_image_choice]\n"
        "variants = [\"alpine\", \"debian-slim\", \"ubuntu\", \"distroless\", \"temurin\"]\n\n"
        "[benchmark.run]\n"
        f'profile = "{profile}"\n'
        "runner_args = [\"--skip-native\"]\n"
        "# cpuset_cpus = \"0-1\"\n"
        "# memory_limit = \"2g\"\n"
        "# warmup_runs = 1\n"
        "# max_workers = 1\n"
        "# normalized_runtime = false\n"
        "legacy_scripts = false\n"
    )


def write_default_config(path: Path, build_tool: str, profile: str = "quick", force: bool = False) -> None:
    """Write starter config file; fail if present unless force=True."""
    if path.exists() and not force:
        raise FileExistsError(f"Config already exists: {path}")
    path.write_text(render_default_config(build_tool=build_tool, profile=profile), encoding="utf-8")


def _expect_table(root: dict[str, Any], key: str) -> dict[str, Any]:
    value = root.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{key}' must be a TOML table")
    return value


def _expect_optional_str(value: Any, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Config key '{key}' must be a string")
    return value


def _expect_optional_int(value: Any, key: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"Config key '{key}' must be an integer")
    return value


def _expect_optional_bool(value: Any, key: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"Config key '{key}' must be a boolean")
    return value


def _expect_optional_str_list(value: Any, key: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"Config key '{key}' must be an array of strings")
    return list(value)


def _validate_schema(data: dict[str, Any]) -> None:
    allowed_top = {"project", "doctor", "dockerfile", "benchmark"}
    unknown_top = sorted(set(data.keys()) - allowed_top)
    if unknown_top:
        raise ValueError(f"Unknown config section(s): {', '.join(unknown_top)}")

    project = _expect_table(data, "project")
    doctor = _expect_table(data, "doctor")
    dockerfile = _expect_table(data, "dockerfile")
    benchmark = _expect_table(data, "benchmark")
    benchmark_run = benchmark.get("run", {})
    benchmark_generate = benchmark.get("generate", {})
    if benchmark_run and not isinstance(benchmark_run, dict):
        raise ValueError("Config section 'benchmark.run' must be a TOML table")
    if benchmark_generate and not isinstance(benchmark_generate, dict):
        raise ValueError("Config section 'benchmark.generate' must be a TOML table")

    for section_name, section, allowed_keys in [
        ("project", project, {"build_tool"}),
        ("doctor", doctor, {"build_tool"}),
        (
            "dockerfile",
            dockerfile,
            {"output", "java_version", "recipe", "must_have_modules_file", "legacy_scripts", "wizard_args"},
        ),
        ("benchmark", benchmark, {"run", "generate", "profile", "runner_args"}),
        (
            "benchmark.run",
            benchmark_run,
            {"profile", "runner_args", "cpuset_cpus", "memory_limit", "warmup_runs", "max_workers", "normalized_runtime", "legacy_scripts"},
        ),
        ("benchmark.generate", benchmark_generate, {"java_version", "legacy_scripts", "base_image_choice"}),
    ]:
        unknown = sorted(set(section.keys()) - allowed_keys)
        if unknown:
            raise ValueError(f"Unknown config key(s) in [{section_name}]: {', '.join(unknown)}")

    _expect_optional_str(project.get("build_tool"), "project.build_tool")
    _expect_optional_str(doctor.get("build_tool"), "doctor.build_tool")
    _expect_optional_str(dockerfile.get("output"), "dockerfile.output")
    _expect_optional_int(dockerfile.get("java_version"), "dockerfile.java_version")
    _expect_optional_str(dockerfile.get("recipe"), "dockerfile.recipe")
    _expect_optional_str(dockerfile.get("must_have_modules_file"), "dockerfile.must_have_modules_file")
    _expect_optional_bool(dockerfile.get("legacy_scripts"), "dockerfile.legacy_scripts")
    _expect_optional_str_list(dockerfile.get("wizard_args"), "dockerfile.wizard_args")
    _expect_optional_str(benchmark_run.get("profile"), "benchmark.run.profile")
    _expect_optional_str_list(benchmark_run.get("runner_args"), "benchmark.run.runner_args")
    _expect_optional_str(benchmark_run.get("cpuset_cpus"), "benchmark.run.cpuset_cpus")
    _expect_optional_str(benchmark_run.get("memory_limit"), "benchmark.run.memory_limit")
    _expect_optional_int(benchmark_run.get("warmup_runs"), "benchmark.run.warmup_runs")
    _expect_optional_int(benchmark_run.get("max_workers"), "benchmark.run.max_workers")
    _expect_optional_bool(benchmark_run.get("normalized_runtime"), "benchmark.run.normalized_runtime")
    _expect_optional_bool(benchmark_run.get("legacy_scripts"), "benchmark.run.legacy_scripts")
    _expect_optional_int(benchmark_generate.get("java_version"), "benchmark.generate.java_version")
    _expect_optional_bool(benchmark_generate.get("legacy_scripts"), "benchmark.generate.legacy_scripts")
    base_image_choice = benchmark_generate.get("base_image_choice")
    if base_image_choice is not None:
        if not isinstance(base_image_choice, dict):
            raise ValueError("Config section 'benchmark.generate.base_image_choice' must be a TOML table")
        unknown_base = sorted(set(base_image_choice.keys()) - {"variants"})
        if unknown_base:
            raise ValueError(
                "Unknown config key(s) in [benchmark.generate.base_image_choice]: " + ", ".join(unknown_base)
            )
        _expect_optional_str_list(base_image_choice.get("variants"), "benchmark.generate.base_image_choice.variants")

    # Backward compatible legacy keys under [benchmark].
    _expect_optional_str(benchmark.get("profile"), "benchmark.profile")
    _expect_optional_str_list(benchmark.get("runner_args"), "benchmark.runner_args")


def load_config(path: Path, strict: bool = True) -> dict[str, Any]:
    """Load TOML config file; return empty dict when file is absent."""
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Config root must be a TOML table")
    if strict:
        _validate_schema(data)
    return data


def _resolve_build_tool(cli_build_tool: str | None, loaded_config: dict[str, Any], section: str) -> str | None:
    value: str | None
    if cli_build_tool is not None:
        value = cli_build_tool
    else:
        target = _expect_table(loaded_config, section)
        project = _expect_table(loaded_config, "project")
        value = _expect_optional_str(target.get("build_tool"), f"{section}.build_tool") or _expect_optional_str(
            project.get("build_tool"), "project.build_tool"
        )
    if value is not None and value not in {"maven", "gradle"}:
        raise ValueError("build tool must be 'maven' or 'gradle'")
    return value


def resolve_doctor_config(cli_build_tool: str | None, loaded_config: dict[str, Any]) -> DoctorConfig:
    return DoctorConfig(build_tool=_resolve_build_tool(cli_build_tool, loaded_config, "doctor"))


def resolve_dockerfile_generate_config(
    cli_build_tool: str | None,
    cli_output: str | None,
    cli_java_version: int | None,
    cli_recipe: str | None,
    cli_wizard_args: list[str] | None,
    cli_use_legacy_scripts: bool | None,
    loaded_config: dict[str, Any],
) -> DockerfileGenerateConfig:
    dockerfile = _expect_table(loaded_config, "dockerfile")
    build_tool = _resolve_build_tool(cli_build_tool, loaded_config, "project")
    output = cli_output or _expect_optional_str(dockerfile.get("output"), "dockerfile.output") or "Dockerfile.generated"
    java_version = cli_java_version or _expect_optional_int(dockerfile.get("java_version"), "dockerfile.java_version") or 25
    recipe = cli_recipe or _expect_optional_str(dockerfile.get("recipe"), "dockerfile.recipe") or "jvm-balanced"
    must_have_modules_file = _expect_optional_str(
        dockerfile.get("must_have_modules_file"),
        "dockerfile.must_have_modules_file",
    )

    if cli_wizard_args is not None:
        wizard_args = cli_wizard_args
    else:
        wizard_args = _expect_optional_str_list(dockerfile.get("wizard_args"), "dockerfile.wizard_args") or []

    if cli_use_legacy_scripts is not None:
        use_legacy = cli_use_legacy_scripts
    else:
        use_legacy = _expect_optional_bool(dockerfile.get("legacy_scripts"), "dockerfile.legacy_scripts") or False

    return DockerfileGenerateConfig(
        build_tool=build_tool,
        output=output,
        java_version=java_version,
        recipe=recipe,
        must_have_modules_file=must_have_modules_file,
        wizard_args=wizard_args,
        use_legacy_scripts=use_legacy,
    )


def resolve_benchmark_generate_config(
    cli_build_tool: str | None,
    cli_java_version: int | None,
    cli_use_legacy_scripts: bool | None,
    loaded_config: dict[str, Any],
) -> BenchmarkGenerateConfig:
    benchmark = _expect_table(loaded_config, "benchmark")
    generate = benchmark.get("generate", {})
    if generate and not isinstance(generate, dict):
        raise ValueError("Config section 'benchmark.generate' must be a TOML table")

    build_tool = _resolve_build_tool(cli_build_tool, loaded_config, "project")
    java_version = cli_java_version or _expect_optional_int(generate.get("java_version"), "benchmark.generate.java_version") or 25
    if cli_use_legacy_scripts is not None:
        use_legacy = cli_use_legacy_scripts
    else:
        use_legacy = _expect_optional_bool(generate.get("legacy_scripts"), "benchmark.generate.legacy_scripts") or False

    base_image_choice = generate.get("base_image_choice", {})
    if base_image_choice and not isinstance(base_image_choice, dict):
        raise ValueError("Config section 'benchmark.generate.base_image_choice' must be a TOML table")
    configured_variants = (
        _expect_optional_str_list(base_image_choice.get("variants"), "benchmark.generate.base_image_choice.variants")
        if isinstance(base_image_choice, dict)
        else None
    )
    base_image_variants = parse_base_image_variants(configured_variants)

    return BenchmarkGenerateConfig(
        build_tool=build_tool,
        java_version=java_version,
        use_legacy_scripts=use_legacy,
        base_image_variants=base_image_variants,
    )


def resolve_benchmark_run_config(
    cli_build_tool: str | None,
    cli_profile: str | None,
    cli_runner_args: list[str] | None,
    cli_cpuset_cpus: str | None,
    cli_memory_limit: str | None,
    cli_warmup_runs: int | None,
    cli_max_workers: int | None,
    cli_normalized_runtime: bool | None,
    cli_use_legacy_scripts: bool | None,
    loaded_config: dict[str, Any],
) -> BenchmarkRunConfig:
    """Merge benchmark-run settings with precedence: CLI > config > defaults."""
    benchmark = _expect_table(loaded_config, "benchmark")
    run_cfg = benchmark.get("run", {})
    if run_cfg and not isinstance(run_cfg, dict):
        raise ValueError("Config section 'benchmark.run' must be a TOML table")

    build_tool = _resolve_build_tool(cli_build_tool, loaded_config, "project")
    legacy_profile = _expect_optional_str(benchmark.get("profile"), "benchmark.profile")
    legacy_runner_args = _expect_optional_str_list(benchmark.get("runner_args"), "benchmark.runner_args")
    profile = cli_profile or _expect_optional_str(run_cfg.get("profile"), "benchmark.run.profile") or legacy_profile or "quick"
    if profile not in {"quick", "full"}:
        raise ValueError("benchmark profile must be 'quick' or 'full'")

    if cli_runner_args is not None:
        runner_args = cli_runner_args
    else:
        runner_args = (
            _expect_optional_str_list(run_cfg.get("runner_args"), "benchmark.run.runner_args")
            or legacy_runner_args
            or []
        )

    cpuset_cpus: str | None
    if cli_cpuset_cpus is not None:
        cpuset_cpus = cli_cpuset_cpus
    else:
        cpuset_cpus = _expect_optional_str(run_cfg.get("cpuset_cpus"), "benchmark.run.cpuset_cpus")

    memory_limit: str | None
    if cli_memory_limit is not None:
        memory_limit = cli_memory_limit
    else:
        memory_limit = _expect_optional_str(run_cfg.get("memory_limit"), "benchmark.run.memory_limit")

    warmup_runs: int
    if cli_warmup_runs is not None:
        warmup_runs = cli_warmup_runs
    else:
        raw_warmup_runs = _expect_optional_int(run_cfg.get("warmup_runs"), "benchmark.run.warmup_runs")
        warmup_runs = raw_warmup_runs if raw_warmup_runs is not None else 0
    if warmup_runs < 0:
        raise ValueError("benchmark.run.warmup_runs must be >= 0")

    max_workers: int
    if cli_max_workers is not None:
        max_workers = cli_max_workers
    else:
        raw_max_workers = _expect_optional_int(run_cfg.get("max_workers"), "benchmark.run.max_workers")
        max_workers = raw_max_workers if raw_max_workers is not None else 1
    if max_workers < 1:
        raise ValueError("benchmark.run.max_workers must be >= 1")

    normalized_runtime: bool
    if cli_normalized_runtime is not None:
        normalized_runtime = cli_normalized_runtime
    else:
        raw_normalized_runtime = _expect_optional_bool(
            run_cfg.get("normalized_runtime"),
            "benchmark.run.normalized_runtime",
        )
        normalized_runtime = raw_normalized_runtime if raw_normalized_runtime is not None else False

    use_legacy: bool
    if cli_use_legacy_scripts is not None:
        use_legacy = cli_use_legacy_scripts
    else:
        raw_use_legacy = _expect_optional_bool(run_cfg.get("legacy_scripts"), "benchmark.run.legacy_scripts")
        use_legacy = raw_use_legacy if raw_use_legacy is not None else False

    return BenchmarkRunConfig(
        build_tool=build_tool,
        profile=profile,
        runner_args=runner_args,
        cpuset_cpus=cpuset_cpus,
        memory_limit=memory_limit,
        warmup_runs=warmup_runs,
        max_workers=max_workers,
        normalized_runtime=normalized_runtime,
        use_legacy_scripts=use_legacy,
    )
