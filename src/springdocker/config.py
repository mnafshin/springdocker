from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from springdocker.runtime_images import parse_base_image_variants

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - exercised on Python < 3.11
    import tomli as tomllib


# Sentinel: auto-detect actuator healthcheck at generate time.
HEALTHCHECK_AUTO = "__auto__"


@dataclass(frozen=True)
class DoctorConfig:
    build_tool: str | None


@dataclass(frozen=True)
class DockerfileGenerateConfig:
    build_tool: str | None
    output: str
    java_version: int
    recipe: str
    profile: str | None
    must_have_modules_file: str | None
    jlink_baseline_modules: tuple[str, ...] | None
    runtime_image: str
    use_buildkit_cache: bool
    use_jlink: bool
    use_layered_jar: bool
    non_root: bool
    platform_aware: bool
    enable_appcds: bool
    enable_jep483_aot_cache: bool
    include_oci_labels: bool
    include_stopsignal: bool
    include_embedded_sbom: bool
    include_reproducible_controls: bool
    pin_digests: bool
    tuned_jvm_flags: bool
    jvm_flags: tuple[str, ...]
    healthcheck_path: str


def sample_dockerfile_config(**overrides: object) -> DockerfileGenerateConfig:
    defaults: dict[str, object] = {
        "build_tool": None,
        "output": "Dockerfile.generated",
        "java_version": 17,
        "recipe": "jvm-balanced",
        "profile": None,
        "must_have_modules_file": None,
        "jlink_baseline_modules": None,
        "runtime_image": "distroless",
        "use_buildkit_cache": True,
        "use_jlink": True,
        "use_layered_jar": True,
        "non_root": True,
        "platform_aware": True,
        "enable_appcds": True,
        "enable_jep483_aot_cache": False,
        "include_oci_labels": True,
        "include_stopsignal": True,
        "include_embedded_sbom": True,
        "include_reproducible_controls": True,
        "pin_digests": True,
        "tuned_jvm_flags": True,
        "jvm_flags": (),
        "healthcheck_path": HEALTHCHECK_AUTO,
    }
    defaults.update(overrides)
    return DockerfileGenerateConfig(**defaults)  # type: ignore[arg-type]


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
        "java_version = 17\n"
        'recipe = "jvm-balanced"\n'
        "# Default generator runtime: distroless (gcr.io/distroless/base-* + jlink + layered JAR).\n"
        "# OS bases (debian-slim, alpine, ubuntu, temurin) are benchmark/generator options — see cli/README.md.\n"
        "# Distroless has no shell; HEALTHCHECK is omitted — use orchestrator readiness probes.\n"
        '# recipe = "native-aot"  # scaffold only; see docs/native-aot.md\n'
        '# must_have_modules_file = "must-have.txt"\n'
        "# When jlink is enabled, these modules are auto-merged into the jlink module list.\n"
        '# jlink_baseline_modules = ["java.desktop", "java.logging", "java.naming", "java.management"]\n'
        "# Omit jlink_baseline_modules to auto-detect from Spring Web starters at generate time.\n"
        "# Set jlink_baseline_modules = [] to disable built-in baseline injection.\n"
        "# Config-first workflow: run `springdocker configure` to set options interactively.\n"
        "# runtime_image = \"distroless\"\n"
        "# use_jlink = true\n"
        "# enable_appcds = true  # available on Java 17+\n"
        "# enable_jep483_aot_cache = true  # requires Java 24+; mutually exclusive with AppCDS\n"
        "# include_embedded_sbom = true\n"
        "# pin_digests = true\n"
        "# tuned_jvm_flags = true\n\n"
        "[benchmark.generate]\n"
        "java_version = 17\n"
        "legacy_scripts = false\n\n"
        "[benchmark.generate.base_image_choice]\n"
        "variants = [\"alpine\", \"debian-slim\", \"ubuntu\", \"distroless\"]\n\n"
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
            {
                "output",
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
            },
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
    _expect_optional_str_list(dockerfile.get("jlink_baseline_modules"), "dockerfile.jlink_baseline_modules")
    _expect_optional_str(dockerfile.get("profile"), "dockerfile.profile")
    _expect_optional_str(dockerfile.get("runtime_image"), "dockerfile.runtime_image")
    _expect_optional_bool(dockerfile.get("use_buildkit_cache"), "dockerfile.use_buildkit_cache")
    _expect_optional_bool(dockerfile.get("use_jlink"), "dockerfile.use_jlink")
    _expect_optional_bool(dockerfile.get("use_layered_jar"), "dockerfile.use_layered_jar")
    _expect_optional_bool(dockerfile.get("non_root"), "dockerfile.non_root")
    _expect_optional_bool(dockerfile.get("platform_aware"), "dockerfile.platform_aware")
    _expect_optional_bool(dockerfile.get("enable_appcds"), "dockerfile.enable_appcds")
    _expect_optional_bool(dockerfile.get("enable_jep483_aot_cache"), "dockerfile.enable_jep483_aot_cache")
    _expect_optional_bool(dockerfile.get("include_oci_labels"), "dockerfile.include_oci_labels")
    _expect_optional_bool(dockerfile.get("include_stopsignal"), "dockerfile.include_stopsignal")
    _expect_optional_bool(dockerfile.get("include_embedded_sbom"), "dockerfile.include_embedded_sbom")
    _expect_optional_bool(dockerfile.get("include_reproducible_controls"), "dockerfile.include_reproducible_controls")
    _expect_optional_bool(dockerfile.get("pin_digests"), "dockerfile.pin_digests")
    _expect_optional_bool(dockerfile.get("tuned_jvm_flags"), "dockerfile.tuned_jvm_flags")
    _expect_optional_str_list(dockerfile.get("jvm_flags"), "dockerfile.jvm_flags")
    healthcheck_path = dockerfile.get("healthcheck_path")
    if healthcheck_path is not None and not isinstance(healthcheck_path, str):
        raise ValueError("Config key 'dockerfile.healthcheck_path' must be a string or null")
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


def _pick_bool(
    cli_value: bool | None,
    config_value: bool | None,
    default: bool,
) -> bool:
    if cli_value is not None:
        return cli_value
    if config_value is not None:
        return config_value
    return default


def _pick_str(
    cli_value: str | None,
    config_value: str | None,
    default: str,
) -> str:
    if cli_value is not None:
        return cli_value
    if config_value is not None:
        return config_value
    return default


def _pick_int(
    cli_value: int | None,
    config_value: int | None,
    default: int,
    *,
    detected_value: int | None = None,
) -> int:
    if cli_value is not None:
        return cli_value
    if config_value is not None:
        return config_value
    if detected_value is not None:
        return detected_value
    return default


def resolve_dockerfile_generate_config(
    cli_build_tool: str | None,
    cli_output: str | None,
    cli_java_version: int | None,
    cli_recipe: str | None,
    cli_profile: str | None,
    cli_runtime_image: str | None,
    cli_use_buildkit_cache: bool | None,
    cli_use_jlink: bool | None,
    cli_use_layered_jar: bool | None,
    cli_non_root: bool | None,
    cli_platform_aware: bool | None,
    cli_enable_appcds: bool | None,
    cli_enable_jep483_aot_cache: bool | None,
    cli_include_oci_labels: bool | None,
    cli_include_stopsignal: bool | None,
    cli_include_embedded_sbom: bool | None,
    cli_include_reproducible_controls: bool | None,
    cli_pin_digests: bool | None,
    cli_tuned_jvm_flags: bool | None,
    cli_jvm_flags: list[str] | None,
    cli_healthcheck_path: str | None,
    loaded_config: dict[str, Any],
    detected_java_version: int | None = None,
) -> DockerfileGenerateConfig:
    dockerfile = _expect_table(loaded_config, "dockerfile")
    build_tool = _resolve_build_tool(cli_build_tool, loaded_config, "project")
    output = cli_output or _expect_optional_str(dockerfile.get("output"), "dockerfile.output") or "Dockerfile.generated"
    java_version = _pick_int(
        cli_java_version,
        _expect_optional_int(dockerfile.get("java_version"), "dockerfile.java_version"),
        17,
        detected_value=detected_java_version,
    )
    recipe = cli_recipe or _expect_optional_str(dockerfile.get("recipe"), "dockerfile.recipe") or "jvm-balanced"
    profile = cli_profile or _expect_optional_str(dockerfile.get("profile"), "dockerfile.profile")
    must_have_modules_file = _expect_optional_str(
        dockerfile.get("must_have_modules_file"),
        "dockerfile.must_have_modules_file",
    )
    if "jlink_baseline_modules" in dockerfile:
        jlink_baseline_modules_raw = _expect_optional_str_list(
            dockerfile.get("jlink_baseline_modules"),
            "dockerfile.jlink_baseline_modules",
        )
        jlink_baseline_modules = () if jlink_baseline_modules_raw is None else tuple(jlink_baseline_modules_raw)
    else:
        jlink_baseline_modules = None

    jvm_flags_raw = (
        cli_jvm_flags
        if cli_jvm_flags is not None
        else _expect_optional_str_list(dockerfile.get("jvm_flags"), "dockerfile.jvm_flags")
    )
    jvm_flags = tuple(jvm_flags_raw) if jvm_flags_raw is not None else ()

    if cli_healthcheck_path is not None:
        healthcheck_path = cli_healthcheck_path
    elif "healthcheck_path" in dockerfile:
        configured = dockerfile.get("healthcheck_path")
        if configured is None:
            healthcheck_path = HEALTHCHECK_AUTO
        elif isinstance(configured, str):
            healthcheck_path = configured
        else:
            raise ValueError("Config key 'dockerfile.healthcheck_path' must be a string or null")
    else:
        healthcheck_path = HEALTHCHECK_AUTO

    return DockerfileGenerateConfig(
        build_tool=build_tool,
        output=output,
        java_version=java_version,
        recipe=recipe,
        profile=profile,
        must_have_modules_file=must_have_modules_file,
        jlink_baseline_modules=jlink_baseline_modules,
        runtime_image=_pick_str(
            cli_runtime_image,
            _expect_optional_str(dockerfile.get("runtime_image"), "dockerfile.runtime_image"),
            "distroless",
        ),
        use_buildkit_cache=_pick_bool(
            cli_use_buildkit_cache,
            _expect_optional_bool(dockerfile.get("use_buildkit_cache"), "dockerfile.use_buildkit_cache"),
            True,
        ),
        use_jlink=_pick_bool(
            cli_use_jlink,
            _expect_optional_bool(dockerfile.get("use_jlink"), "dockerfile.use_jlink"),
            True,
        ),
        use_layered_jar=_pick_bool(
            cli_use_layered_jar,
            _expect_optional_bool(dockerfile.get("use_layered_jar"), "dockerfile.use_layered_jar"),
            True,
        ),
        non_root=_pick_bool(
            cli_non_root,
            _expect_optional_bool(dockerfile.get("non_root"), "dockerfile.non_root"),
            True,
        ),
        platform_aware=_pick_bool(
            cli_platform_aware,
            _expect_optional_bool(dockerfile.get("platform_aware"), "dockerfile.platform_aware"),
            True,
        ),
        enable_appcds=_pick_bool(
            cli_enable_appcds,
            _expect_optional_bool(dockerfile.get("enable_appcds"), "dockerfile.enable_appcds"),
            True,
        ),
        enable_jep483_aot_cache=_pick_bool(
            cli_enable_jep483_aot_cache,
            _expect_optional_bool(dockerfile.get("enable_jep483_aot_cache"), "dockerfile.enable_jep483_aot_cache"),
            False,
        ),
        include_oci_labels=_pick_bool(
            cli_include_oci_labels,
            _expect_optional_bool(dockerfile.get("include_oci_labels"), "dockerfile.include_oci_labels"),
            True,
        ),
        include_stopsignal=_pick_bool(
            cli_include_stopsignal,
            _expect_optional_bool(dockerfile.get("include_stopsignal"), "dockerfile.include_stopsignal"),
            True,
        ),
        include_embedded_sbom=_pick_bool(
            cli_include_embedded_sbom,
            _expect_optional_bool(dockerfile.get("include_embedded_sbom"), "dockerfile.include_embedded_sbom"),
            True,
        ),
        include_reproducible_controls=_pick_bool(
            cli_include_reproducible_controls,
            _expect_optional_bool(dockerfile.get("include_reproducible_controls"), "dockerfile.include_reproducible_controls"),
            True,
        ),
        pin_digests=_pick_bool(
            cli_pin_digests,
            _expect_optional_bool(dockerfile.get("pin_digests"), "dockerfile.pin_digests"),
            True,
        ),
        tuned_jvm_flags=_pick_bool(
            cli_tuned_jvm_flags,
            _expect_optional_bool(dockerfile.get("tuned_jvm_flags"), "dockerfile.tuned_jvm_flags"),
            True,
        ),
        jvm_flags=jvm_flags,
        healthcheck_path=healthcheck_path,
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
    java_version = cli_java_version or _expect_optional_int(generate.get("java_version"), "benchmark.generate.java_version") or 17
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
