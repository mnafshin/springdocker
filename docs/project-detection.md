# Project detection

`springdocker` detects Maven and Gradle projects with **marker checks** and lightweight descriptor parsing.
It is optimized for typical single-module Spring Boot apps and common multi-module layouts — not every exotic monorepo.

See also: [`extensions.md`](extensions.md) (project detector plugins), [`troubleshooting.md`](troubleshooting.md).

## What is detected automatically

| Signal | Maven | Gradle |
|---|---|---|
| Build tool | Root `pom.xml` | `gradlew` and/or `build.gradle(.kts)` |
| Spring Boot markers | `spring-boot` in root descriptor, or `application.properties/yml` under `src/main/resources` | Same |
| Java / Boot versions | Root `pom.xml` properties/parent, or `build.gradle(.kts)` plugins/toolchain | Same |
| Multi-module layout | `<packaging>pom</packaging>` + `<modules>` in root POM | `include(...)` in `settings.gradle(.kts)` |
| Spring Boot module | Markers in a listed submodule | Markers in an included subproject |

`springdocker inspect` reports `layout`, `modules`, and `spring_boot_modules` and adds recommendations when the Spring app is not at the repository root.

## Detection boundaries (not supported out of the box)

| Layout | Limitation | Path forward |
|---|---|---|
| Maven reactor, app in submodule | Root aggregator POM may lack Spring dependencies | Run CLI with `--project-root path/to/service` or use inspect recommendations |
| Gradle composite / nested includes | Only direct `include("name")` entries in settings files are scanned | Point `--project-root` at the bootable subproject |
| `includeBuild` / Gradle plugin builds | Not parsed | Custom `springdocker.project_detectors` plugin |
| Bazel, sbt, Ant | No markers | Custom detector plugin + explicit `--build-tool` where applicable |
| Mixed Maven + Gradle markers at root | Ambiguous | Pass `--build-tool maven` or `gradle` |
| Spring Boot only in BOM/imported parent | Root POM may not mention `spring-boot` string | Inspect submodule metadata or set project root to the service module |
| Kotlin DSL with dynamic includes | Static regex may miss generated module lists | Plugin or run from the service directory |

## Recommended workflows

### Single-module app (default)

```bash
springdocker doctor --project-root .
springdocker dockerfile generate --project-root .
```

### Maven reactor (monorepo)

Repository layout:

```text
pom.xml                 # packaging pom, lists modules
services/
  api/
    pom.xml             # spring-boot-starter-* dependencies
    src/main/java/...
```

From repository root:

```bash
springdocker inspect --project-root . --format json
# → layout: maven-reactor, spring_boot_modules: ["services/api"]
```

Generate from the **service module**:

```bash
springdocker init --project-root services/api --build-tool maven
springdocker dockerfile generate --project-root services/api
```

### Gradle multi-project

```text
settings.gradle.kts     # include("app")
app/
  build.gradle.kts      # org.springframework.boot plugin
```

Same pattern: inspect at root, generate from `app/` (or whichever module is bootable).

## Plugin escape hatch

Register a detector when markers are non-standard (custom wrapper scripts, generated settings, polyglot repos):

```toml
[project.entry-points."springdocker.project_detectors"]
acme-monorepo = "acme_plugins.detectors:detect_build_tool"
```

Examples:

- [`docs/examples/extensions/custom_project_detector.py`](examples/extensions/custom_project_detector.py) — minimal override
- [`docs/examples/extensions/maven_reactor_project_detector.py`](examples/extensions/maven_reactor_project_detector.py) — choose build tool from reactor layout
- [`docs/examples/extensions/gradle_monorepo_project_detector.py`](examples/extensions/gradle_monorepo_project_detector.py) — composite-build hints

Plugins run **before** built-in marker detection. Return `"maven"`, `"gradle"`, or `None`.

## Configuration override

Set build tool explicitly when detection is correct but you want config defaults pinned:

```toml
[project]
build_tool = "maven"
```

Or pass `--build-tool` on each command.

## CI / golden samples

End-to-end tests use minimal single-module fixtures under `tests/fixtures/`.
Multi-module behavior is covered by unit tests on `project_detect.py` — not full Dockerfile e2e on every reactor shape.
