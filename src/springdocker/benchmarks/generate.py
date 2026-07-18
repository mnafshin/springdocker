from __future__ import annotations

import shutil
from dataclasses import dataclass, replace
from pathlib import Path

from springdocker.config import DockerfileGenerateConfig
from springdocker.dockerfile import BUILTIN_RECIPES, DockerfileOptions, build_dockerfile
from springdocker.java_features import jep483_supported
from springdocker.runtime_images import DEFAULT_BASE_IMAGE_VARIANTS, variant_slug
from springdocker.services import dockerfile_service

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

See `docs/native-aot.md` in the springdocker repository for scaffold status.
"""

EXAMPLE_DOCKERFILES_README = """\
# Example generated Dockerfiles

Versioned reference output from `springdocker` for the three built-in recipe presets on this sample project.
Recipe files inherit `[dockerfile]` settings from `.springdocker.toml` (only `recipe` varies per file).

Regenerate together with benchmark assets:

```bash
springdocker benchmark generate --project-root . --java-version 25
```

Scenario variant Dockerfiles live under `benchmarks/<scenario>/variants/` (gitignored, same command).

Source: https://github.com/mnafshin/springdocker
"""

EXAMPLE_RECIPE_DOCKERFILES_README = """\
# Recipe presets

Reference Dockerfiles for each built-in `springdocker` recipe on the sample project's build tool.
Options come from the project's `.springdocker.toml` `[dockerfile]` section (runtime base, jlink, SBOM,
AppCDS, pinned digests, and so on); only the `recipe` field changes per file.

| File | Recipe | Purpose |
|---|---|---|
| `jvm-balanced.Dockerfile` | `jvm-balanced` | Default layered-JAR multi-stage JVM image |
| `spring-aot.Dockerfile` | `spring-aot` | Spring AOT processing in the build stage |
| `native-aot.Dockerfile` | `native-aot` | GraalVM native-image scaffold (experimental) |

## Runtime default (scenario 03 evidence)

Pinned sample results for jlink on each OS base (`benchmarks/03-base-image-choice/results/baseline.json`):

| Base | Image avg | Build avg | Startup avg |
|---|---:|---:|---:|
| alpine | 62.4 MB | 936 ms | 1,583 ms |
| **distroless** | **67.7 MB** | 959 ms | **1,511 ms** |
| debian-slim | 85.9 MB | **616 ms** | 1,584 ms |
| ubuntu | 85.9 MB | 984 ms | 1,673 ms |

`jvm-balanced` and `spring-aot` default to **distroless**: smaller than debian-slim (~21%) with faster startup,
at the cost of slower image builds. Pick alpine when every MB counts (verify musl). Pick debian-slim when build
speed matters most.

Regenerate with:

```bash
springdocker benchmark generate --project-root . --java-version 25
```

Select a recipe when generating ad hoc output:

```bash
springdocker generate --project-root . --recipe spring-aot
```

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
    return DockerfileOptions(
        build_tool=build_tool,
        java_version=java_version,
        must_have_modules=must_have_modules,
        use_jlink=True,
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
    scenarios: list[ScenarioDefinition] = [
        StandardScenarioDefinition(
            id="01-custom-jre-jlink",
            variants=(
                (
                    "with-jlink-runtime",
                    DockerfileOptions(
                        build_tool=build_tool,
                        java_version=java_version,
                        must_have_modules=must_have_modules,
                        runtime_image="debian-slim",
                        use_jlink=True,
                        enable_appcds=False,
                        enable_jep483_aot_cache=False,
                    ),
                ),
                (
                    "without-jlink-runtime",
                    DockerfileOptions(
                        build_tool=build_tool,
                        java_version=java_version,
                        must_have_modules=must_have_modules,
                        runtime_image="debian-slim",
                        use_jlink=False,
                        enable_appcds=False,
                        enable_jep483_aot_cache=False,
                    ),
                ),
                (
                    "temurin-jre-image",
                    DockerfileOptions(
                        build_tool=build_tool,
                        java_version=java_version,
                        must_have_modules=must_have_modules,
                        runtime_image="temurin",
                        use_jlink=False,
                        enable_appcds=False,
                        enable_jep483_aot_cache=False,
                    ),
                ),
            ),
        ),
    ]
    if jep483_supported(java_version):
        scenarios.append(
            StandardScenarioDefinition(
                id="02-jep483-aot-cache",
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
            )
        )
    scenarios.extend(
        [
            StandardScenarioDefinition(
                id="03-base-image-choice",
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
                id="05-appcds",
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
            NativeScenarioDefinition(id="04-native-benchmark"),
        ]
    )
    return scenarios


def generate_benchmark_assets(
    project_root: Path,
    build_tool: str,
    java_version: int,
    must_have_modules: tuple[str, ...] = (),
    base_image_variants: tuple[str, ...] | None = None,
    dockerfile_config: DockerfileGenerateConfig | None = None,
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
        dockerfile_config=dockerfile_config,
    )


def _recipe_dockerfile_options(
    project_root: Path,
    build_tool: str,
    java_version: int,
    recipe: str,
    dockerfile_config: DockerfileGenerateConfig | None,
    must_have_modules: tuple[str, ...],
) -> DockerfileOptions:
    if dockerfile_config is not None:
        recipe_config = replace(dockerfile_config, recipe=recipe, java_version=java_version)
        return dockerfile_service.dockerfile_options_from_config(project_root, build_tool, recipe_config)
    return DockerfileOptions(
        build_tool=build_tool,
        java_version=java_version,
        recipe=recipe,
        must_have_modules=must_have_modules,
        enable_appcds=False,
        enable_jep483_aot_cache=False,
    )


def _write_example_recipe_dockerfiles(
    example_root: Path,
    project_root: Path,
    build_tool: str,
    java_version: int,
    must_have_modules: tuple[str, ...],
    dockerfile_config: DockerfileGenerateConfig | None,
    expected_paths: set[Path],
) -> None:
    recipes_dir = example_root / "recipes"
    recipes_dir.mkdir(parents=True, exist_ok=True)
    (recipes_dir / "README.md").write_text(EXAMPLE_RECIPE_DOCKERFILES_README, encoding="utf-8")

    for recipe in BUILTIN_RECIPES:
        opts = _recipe_dockerfile_options(
            project_root=project_root,
            build_tool=build_tool,
            java_version=java_version,
            recipe=recipe,
            dockerfile_config=dockerfile_config,
            must_have_modules=must_have_modules,
        )
        dockerfile_path = recipes_dir / f"{recipe}.Dockerfile"
        dockerfile_path.write_text(build_dockerfile(opts), encoding="utf-8")
        expected_paths.add(dockerfile_path)


def generate_example_dockerfiles(
    project_root: Path,
    build_tool: str,
    java_version: int,
    must_have_modules: tuple[str, ...] = (),
    base_image_variants: tuple[str, ...] | None = None,
    dockerfile_config: DockerfileGenerateConfig | None = None,
) -> None:
    del base_image_variants  # recipe examples use generator defaults, not scenario matrices
    example_root = project_root / "example-dockerfiles"
    example_root.mkdir(parents=True, exist_ok=True)
    if example_root.exists():
        for child in example_root.iterdir():
            if child.is_dir() and child.name != "recipes":
                shutil.rmtree(child)

    (example_root / "README.md").write_text(EXAMPLE_DOCKERFILES_README, encoding="utf-8")

    expected_paths: set[Path] = set()
    _write_example_recipe_dockerfiles(
        example_root=example_root,
        project_root=project_root,
        build_tool=build_tool,
        java_version=java_version,
        must_have_modules=must_have_modules,
        dockerfile_config=dockerfile_config,
        expected_paths=expected_paths,
    )

    for existing in example_root.rglob("*"):
        if not existing.is_file() or existing.name == "README.md":
            continue
        if existing not in expected_paths:
            existing.unlink()