from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from springdocker.dockerfile import DockerfileOptions, build_dockerfile
from springdocker.runtime_images import DEFAULT_BASE_IMAGE_VARIANTS, variant_slug

EXPECTED_CSV_HEADER = (
    "date,scenario,variant,run,build_ms,image_bytes,startup_ms,status,notes,host,docker_version,run_profile,"
    "gc_pause_ms,alloc_mb,startup_phase_boot_ms,startup_phase_context_ms,startup_phase_web_server_ms\n"
)

NATIVE_SCENARIO_README = """\
# Native benchmark scaffold

This scenario is generated as **experimental scaffold output only**.

- The Dockerfile uses the `native-aot` recipe preset.
- `springdocker` does not ship a production native-image workflow yet.
- The internal benchmark runner skips this scenario by default (`--skip-native`).

See `docs/native-image-roadmap.md` in the springdocker repository for the planned workflow.
"""

EXAMPLE_DOCKERFILES_README = """\
# Example generated Dockerfiles

Versioned reference output from `springdocker` for each benchmark scenario in this sample project.

Regenerate together with benchmark assets:

```bash
springdocker benchmark generate --project-root samples/java-spring-docker --java-version 25
```

Each `*.Dockerfile` matches the corresponding variant under `benchmarks/<scenario>/variants/` (those variant trees are gitignored and reproduced by the same command).

Source: https://github.com/mnafshin/springdocker
"""


@dataclass(frozen=True)
class ScenarioDefinition:
    id: str


@dataclass(frozen=True)
class StandardScenarioDefinition(ScenarioDefinition):
    variants: tuple[tuple[str, DockerfileOptions], ...]
    run_overrides: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if not self.variants:
            raise ValueError("standard scenario must define at least one variant")


@dataclass(frozen=True)
class NativeScenarioDefinition(ScenarioDefinition):
    pass


def _base_image_variant_options(
    build_tool: str,
    java_version: int,
    must_have_modules: tuple[str, ...],
    runtime_image: str,
) -> DockerfileOptions:
    use_jlink = runtime_image in {"debian-slim", "ubuntu", "alpine"}
    return DockerfileOptions(
        build_tool=build_tool,
        java_version=java_version,
        must_have_modules=must_have_modules,
        use_jlink=use_jlink,
        use_layered_jar=True,
        tuned_jvm_flags=True,
        runtime_image=runtime_image,
        enable_appcds=False,
        enable_jep483_aot_cache=False,
    )


def default_scenarios(
    build_tool: str,
    java_version: int,
    must_have_modules: tuple[str, ...] = (),
    base_image_variants: tuple[str, ...] | None = None,
) -> list[ScenarioDefinition]:
    runtime_bases = base_image_variants if base_image_variants is not None else DEFAULT_BASE_IMAGE_VARIANTS
    base = DockerfileOptions(
        build_tool=build_tool,
        java_version=java_version,
        must_have_modules=must_have_modules,
        enable_appcds=False,
        enable_jep483_aot_cache=False,
    )
    return [
        StandardScenarioDefinition(
            id="01-multi-stage-build-structure",
            variants=(
                ("specialized-multi-stage", base),
                (
                    "simple-two-stage",
                    DockerfileOptions(
                        build_tool=build_tool,
                        java_version=java_version,
                        must_have_modules=must_have_modules,
                        use_jlink=False,
                        use_layered_jar=False,
                        enable_appcds=False,
                        enable_jep483_aot_cache=False,
                    ),
                ),
            ),
        ),
        StandardScenarioDefinition(
            id="02-buildkit-gradle-cache",
            variants=(
                ("with-buildkit-cache", base),
                ("without-buildkit-cache", DockerfileOptions(build_tool=build_tool, java_version=java_version, use_buildkit_cache=False, enable_appcds=False, enable_jep483_aot_cache=False)),
            ),
        ),
        StandardScenarioDefinition(
            id="03-custom-jre-jlink",
            variants=(
                ("with-jlink-runtime", base),
                ("without-jlink-runtime", DockerfileOptions(build_tool=build_tool, java_version=java_version, use_jlink=False, enable_appcds=False, enable_jep483_aot_cache=False)),
            ),
        ),
        StandardScenarioDefinition(
            id="04-jep483-aot-cache",
            variants=(
                (
                    "with-aot-cache",
                    DockerfileOptions(
                        build_tool=build_tool,
                        java_version=java_version,
                        must_have_modules=must_have_modules,
                        enable_jep483_aot_cache=True,
                        enable_appcds=False,
                    ),
                ),
                ("without-aot-cache", base),
            ),
            run_overrides={"quick": 8, "full": 15},
        ),
        StandardScenarioDefinition(
            id="05-jvm-container-flags",
            variants=(
                (
                    "tuned-flags",
                    DockerfileOptions(
                        build_tool=build_tool,
                        java_version=java_version,
                        must_have_modules=must_have_modules,
                        tuned_jvm_flags=True,
                        enable_appcds=False,
                        enable_jep483_aot_cache=False,
                    ),
                ),
                (
                    "defaults-like",
                    DockerfileOptions(
                        build_tool=build_tool,
                        java_version=java_version,
                        must_have_modules=must_have_modules,
                        tuned_jvm_flags=False,
                        enable_appcds=False,
                        enable_jep483_aot_cache=False,
                    ),
                ),
            ),
        ),
        StandardScenarioDefinition(
            id="06-base-image-choice",
            variants=tuple(
                (
                    variant_slug(runtime_image),
                    _base_image_variant_options(
                        build_tool=build_tool,
                        java_version=java_version,
                        must_have_modules=must_have_modules,
                        runtime_image=runtime_image,
                    ),
                )
                for runtime_image in runtime_bases
            ),
        ),
        StandardScenarioDefinition(
            id="08-appcds",
            variants=(
                (
                    "with-appcds",
                    DockerfileOptions(
                        build_tool=build_tool,
                        java_version=java_version,
                        must_have_modules=must_have_modules,
                        enable_appcds=True,
                        enable_jep483_aot_cache=False,
                    ),
                ),
                ("without-appcds", base),
            ),
        ),
        NativeScenarioDefinition(id="07-native-benchmark"),
    ]


def generate_benchmark_assets(
    project_root: Path,
    build_tool: str,
    java_version: int,
    must_have_modules: tuple[str, ...] = (),
    base_image_variants: tuple[str, ...] | None = None,
) -> None:
    bench_root = project_root / "benchmarks"
    bench_root.mkdir(parents=True, exist_ok=True)

    for scenario in default_scenarios(
        build_tool=build_tool,
        java_version=java_version,
        must_have_modules=must_have_modules,
        base_image_variants=base_image_variants,
    ):
        scenario_dir = bench_root / scenario.id
        results_dir = scenario_dir / "results"
        scenario_dir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(scenario, StandardScenarioDefinition):
            variants_dir = scenario_dir / "variants"
            variants_dir.mkdir(parents=True, exist_ok=True)
            expected_variants = {name for name, _ in scenario.variants}
            for existing in variants_dir.iterdir():
                if existing.is_dir() and existing.name not in expected_variants:
                    shutil.rmtree(existing)
            for name, opts in scenario.variants:
                variant_dir = variants_dir / name
                variant_dir.mkdir(parents=True, exist_ok=True)
                (variant_dir / "Dockerfile").write_text(build_dockerfile(opts), encoding="utf-8")
        elif isinstance(scenario, NativeScenarioDefinition):
            # For the native-vs-jvm scenario, generate a single Dockerfile at the scenario root
            native_dockerfile = scenario_dir / "Dockerfile"
            native_opts = DockerfileOptions(
                build_tool=build_tool,
                recipe="native-aot",
                java_version=java_version,
                must_have_modules=must_have_modules,
                enable_appcds=False,
                enable_jep483_aot_cache=False,
            )
            native_dockerfile.write_text(build_dockerfile(native_opts), encoding="utf-8")
            (scenario_dir / "README.md").write_text(NATIVE_SCENARIO_README, encoding="utf-8")
        else:  # pragma: no cover - defensive guard for future extensions
            raise TypeError(f"unsupported scenario definition: {type(scenario)}")

        csv = results_dir / "raw.csv"
        if not csv.exists():
            csv.write_text(EXPECTED_CSV_HEADER, encoding="utf-8")

    generate_example_dockerfiles(
        project_root=project_root,
        build_tool=build_tool,
        java_version=java_version,
        must_have_modules=must_have_modules,
        base_image_variants=base_image_variants,
    )


def generate_example_dockerfiles(
    project_root: Path,
    build_tool: str,
    java_version: int,
    must_have_modules: tuple[str, ...] = (),
    base_image_variants: tuple[str, ...] | None = None,
) -> None:
    example_root = project_root / "example-dockerfiles"
    example_root.mkdir(parents=True, exist_ok=True)
    (example_root / "README.md").write_text(EXAMPLE_DOCKERFILES_README, encoding="utf-8")

    expected_paths: set[Path] = set()
    for scenario in default_scenarios(
        build_tool=build_tool,
        java_version=java_version,
        must_have_modules=must_have_modules,
        base_image_variants=base_image_variants,
    ):
        scenario_dir = example_root / scenario.id
        scenario_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(scenario, StandardScenarioDefinition):
            for name, opts in scenario.variants:
                dockerfile_path = scenario_dir / f"{name}.Dockerfile"
                dockerfile_path.write_text(build_dockerfile(opts), encoding="utf-8")
                expected_paths.add(dockerfile_path)
        elif isinstance(scenario, NativeScenarioDefinition):
            native_opts = DockerfileOptions(
                build_tool=build_tool,
                recipe="native-aot",
                java_version=java_version,
                must_have_modules=must_have_modules,
                enable_appcds=False,
                enable_jep483_aot_cache=False,
            )
            dockerfile_path = scenario_dir / "Dockerfile"
            dockerfile_path.write_text(build_dockerfile(native_opts), encoding="utf-8")
            expected_paths.add(dockerfile_path)
        else:  # pragma: no cover - defensive guard for future extensions
            raise TypeError(f"unsupported scenario definition: {type(scenario)}")

    for existing in example_root.rglob("*"):
        if not existing.is_file() or existing.name == "README.md":
            continue
        if existing not in expected_paths:
            existing.unlink()
