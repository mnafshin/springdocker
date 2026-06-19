# springdocker CLI

CLI for Spring Boot Dockerfile and benchmark workflows across Maven and Gradle projects.

Product scope and CI-evidenced guarantees: [`docs/POSITIONING.md`](../docs/POSITIONING.md).

## Install

### Local editable

```bash
python3 -m pip install -e .
```

### pipx

```bash
pipx install springdocker
springdocker --help
```

Upgrade:

```bash
pipx upgrade springdocker
```

### uv

```bash
uv tool install springdocker
uv tool upgrade springdocker

# benchmark/evidence commands need optional extras
python3 -m pip install -e '.[benchmark]'
```

## Quick usage

```bash
springdocker init --project-root samples/java-spring-docker --build-tool maven --profile quick
springdocker configure --project-root samples/java-spring-docker --force   # interactive → writes [dockerfile] in config
springdocker dockerfile generate --project-root samples/java-spring-docker  # non-interactive; reads .springdocker.toml
springdocker doctor --project-root samples/java-spring-docker
springdocker inspect --project-root samples/java-spring-docker --format json
springdocker explain --project-root samples/java-spring-docker Dockerfile.generated --format json
springdocker benchmark compare --project-root samples/java-spring-docker benchmarks/03-custom-jre-jlink/results/raw.csv --baseline-variant with-jlink-runtime --format json
springdocker dockerfile generate --project-root samples/java-spring-docker --output Dockerfile.generated --recipe jvm-balanced
springdocker dockerfile generate --project-root samples/java-spring-docker --recipe spring-aot
# native-aot emits experimental scaffold output only (not a production workflow)
springdocker dockerfile generate --project-root samples/java-spring-docker --recipe native-aot
springdocker benchmark generate --project-root samples/java-spring-docker --java-version 25
springdocker benchmark run --project-root samples/java-spring-docker --profile quick --runner-arg --skip-native
springdocker benchmark analyze --project-root samples/java-spring-docker benchmarks/04-jep483-aot-cache/results/raw.csv --format table
springdocker benchmark analyze --project-root samples/java-spring-docker benchmarks/04-jep483-aot-cache/results/raw.csv --format json --output benchmarks/04-jep483-aot-cache/results/summary.json
springdocker benchmark analyze --project-root samples/java-spring-docker benchmarks/04-jep483-aot-cache/results/raw.csv --fail-on-success-rate-below 95
springdocker benchmark analyze --project-root samples/java-spring-docker benchmarks/04-jep483-aot-cache/results/raw.csv --baseline benchmarks/04-jep483-aot-cache/results/baseline.json --fail-on-regression-above 20
```

Benchmark commands are optional evidence workflows and require benchmark extras.
Use `samples/java-spring-docker/benchmarks/06-base-image-choice/results/baseline.json` as the versioned CI regression baseline example (paired with committed `raw.csv`).
Scenario index: [README.md](../README.md#benchmark-scenario-index).

## Dockerfile recipes

| Recipe | Status | Default runtime | Notes |
|---|---|---|---|
| `jvm-balanced` | Supported | **distroless** + jlink | Default production-oriented JVM Dockerfile. |
| `spring-aot` | Supported | **distroless** + jlink | Spring Boot AOT processing on a JVM runtime. |
| `native-aot` | Scaffold only | **distroless** base (static binary) | Experimental GraalVM native-image Dockerfile output. Not a production-ready workflow; see `docs/native-image-roadmap.md`. |

The generator sets `runtime_image = "distroless"` internally for JVM recipes. That means `distroless/base-debian*` plus a copied jlink runtime — not the prebuilt `distroless/java*` image and not a full OS layer unless you change generator options (benchmark scenario **06** compares OS bases).

### Runtime bases and HEALTHCHECK

| Runtime | Generator behavior |
|---|---|
| `distroless` (default) | Non-root, minimal base + jlink; **no `HEALTHCHECK`** (no shell/`wget` in the image). Probe readiness from the orchestrator (e.g. Kubernetes `readinessProbe` on `/actuator/health/readiness`). |
| `debian-slim`, `alpine`, `ubuntu`, `temurin` | Full OS or vendor JRE paths; **`HEALTHCHECK` is emitted** when Spring Boot Actuator is on the classpath. |

Supported runtime names: `distroless`, `debian-slim`, `alpine`, `ubuntu`, `temurin` (plus aliases such as `debian-bookworm-slim`, `eclipse-temurin-jre`). Set via `[dockerfile].runtime_image` in `.springdocker.toml` or `--runtime-image` on `dockerfile generate`.

## Config-first workflow

`.springdocker.toml` is the **single source of truth** for Dockerfile generation (see [ADR 0005](../docs/adr/0005-config-first-dockerfile-generation.md)).

| Command | Purpose |
|---|---|
| `springdocker configure` | Interactive wizard that writes/updates `[dockerfile]` in config |
| `springdocker init --interactive` | Create config skeleton, then run configure |
| `springdocker dockerfile generate` | Deterministic generate from config (CI-safe, no prompts) |

Precedence: **CLI flags > `.springdocker.toml` > defaults**.

Profiles (`production-balanced`, `smallest-image`, `fast-cold-start`, `build-speed`, `simplest`, `compliance`, `custom`) are selected in `configure` and expanded to explicit options in config.

### `dockerfile generate` CLI overrides

Every `[dockerfile]` key is overridable from the CLI except file-backed keys (`must_have_modules_file`, `jlink_baseline_modules`), which stay in config only.

| Section | CLI flags | Config key(s) |
|---|---|---|
| General | `--output`, `--java-version`, `--recipe`, `--profile`, `--use-legacy-scripts`, `--wizard-arg` | `output`, `java_version`, `recipe`, `profile`, `legacy_scripts`, `wizard_args` |
| Runtime | `--runtime-image`, `--non-root` / `--no-non-root`, `--platform-aware` / `--no-platform-aware`, `--healthcheck-path` | `runtime_image`, `non_root`, `platform_aware`, `healthcheck_path` |
| Build | `--use-buildkit-cache` / `--no-use-buildkit-cache`, `--use-jlink` / `--no-use-jlink`, `--use-layered-jar` / `--no-use-layered-jar` | `use_buildkit_cache`, `use_jlink`, `use_layered_jar` |
| Supply chain | `--include-oci-labels`, `--include-stopsignal`, `--include-embedded-sbom`, `--include-reproducible-controls`, `--pin-digests` (each with `--no-*` form) | matching `include_*` keys and `pin_digests` |
| JVM | `--enable-appcds`, `--enable-jep483-aot-cache`, `--tuned-jvm-flags`, `--jvm-flag` (repeatable) | `enable_appcds`, `enable_jep483_aot_cache`, `tuned_jvm_flags`, `jvm_flags` |

Example one-off CI override:

```bash
springdocker dockerfile generate \
  --project-root samples/java-spring-docker \
  --runtime-image alpine \
  --no-use-jlink \
  --enable-jep483-aot-cache \
  --no-include-embedded-sbom \
  --pin-digests \
  --jvm-flag "-XX:+UseZGC"    # or --jvm-flag=-XX:+UseZGC when the flag starts with '-'
```

The `dockerfile generate` `--help` output groups flags under **runtime**, **build**, **supply chain**, and **JVM** sections.

The `07-native-benchmark` scenario is generated with the `native-aot` scaffold recipe. The internal benchmark runner skips native scenarios by default (`--skip-native`).

## Config file (`.springdocker.toml`)

All command resolvers use precedence:

1. CLI flags
2. `.springdocker.toml`
3. defaults

Example:

```toml
[project]
build_tool = "maven"

[doctor]
build_tool = "maven"

[dockerfile]
output = "Dockerfile.generated"
java_version = 25
recipe = "jvm-balanced"
# profile = "production-balanced"  # set by `springdocker configure`
# runtime_image = "distroless"
# use_jlink = true
# enable_jep483_aot_cache = false
# include_embedded_sbom = true
# pin_digests = true
# tuned_jvm_flags = true
# jvm_flags = ["-XX:MaxRAMPercentage=75", "-XX:+ExitOnOutOfMemoryError", "-Djava.io.tmpdir=/tmp"]
# Generator default runtime: distroless (gcr.io/distroless/base-* + jlink + layered JAR).
must_have_modules_file = "must-have.txt"
legacy_scripts = false
wizard_args = []

[benchmark.generate]
java_version = 25
legacy_scripts = false

[benchmark.run]
profile = "quick"
runner_args = ["--skip-native"]
cpuset_cpus = "0-1"
memory_limit = "2g"
warmup_runs = 1
max_workers = 1
normalized_runtime = true
legacy_scripts = false
```

When `dockerfile.must_have_modules_file` is set, springdocker reads modules from that file
(`must-have.txt` style, one module per line, `#` comments allowed) and injects them into
the jlink module list for reflection/dynamic-loading edge cases.

When jlink is enabled, springdocker also auto-merges built-in **jlink baseline modules**:

- `java.desktop` — JavaBeans and desktop-related APIs used by parts of the Spring stack
- `java.logging` — `java.util.logging` used by framework and library code
- `java.naming` — JNDI lookups that jdeps often misses on web apps

Configure or disable them in `.springdocker.toml`:

```toml
[dockerfile]
# Override defaults or set [] to disable baseline injection.
jlink_baseline_modules = ["java.desktop", "java.logging", "java.naming"]
```

`springdocker explain` reports baseline and curated modules separately in JSON/table output.
Baseline modules are generator defaults; curated modules come from `must_have_modules_file`.

Create template config:

```bash
springdocker init --project-root samples/java-spring-docker --build-tool gradle
springdocker init --project-root samples/java-spring-docker --build-tool gradle --profile full --print
```

## Legacy compatibility mode

Main command paths are internal and do not require project script files.

To force script wrappers for compatibility:

```bash
springdocker dockerfile generate --use-legacy-scripts ...
springdocker benchmark generate --use-legacy-scripts ...
springdocker benchmark run --use-legacy-scripts ...
```

or set:

```bash
export SPRINGDOCKER_LEGACY_SCRIPTS=1
```

## Inspect command

`springdocker inspect` prints static metadata about the target project:

- detected build tool
- Spring Boot version when present
- Java version when present
- direct dependency coordinates
- generated Dockerfile artifacts in the project root
- basic runtime compatibility guidance

Use `--format json` for machine-readable output.

## Explain command

`springdocker explain` reads a springdocker-generated Dockerfile and describes the optimizations it contains:

- multi-stage layout
- BuildKit cache usage
- jlink runtime stage
- non-root runtime
- tuned JVM flags
- jlink baseline modules (built-in defaults)
- curated must-have modules (from `must-have.txt`)

Use `--format json` when you want stable structured output.

## Verify command

`springdocker verify` runs a battery of checks against a generated Dockerfile and optional runtime context. It is designed to work in CI without installing every external tool.

```bash
springdocker verify --project-root tests/fixtures/maven-only Dockerfile.generated
springdocker verify --project-root tests/fixtures/maven-only Dockerfile.generated \
  --image demo:latest \
  --smoke-url http://127.0.0.1:8081/actuator/health \
  --format junit \
  --output reports/verify.junit.xml
```

### Built-in checks

| Check | Requires | Missing prerequisite | Check failure |
|---|---|---|---|
| `hadolint` | `hadolint` on `PATH` | **skipped** (`hadolint not installed`) | non-zero exit |
| `trivy` | `trivy` on `PATH` | **skipped** (`trivy not installed`) | HIGH/CRITICAL findings |
| `dive` | `--image` and `dive` on `PATH` | **skipped** (`no image provided` or `dive not installed`) | non-zero exit |
| `cosign` | `--image` and `cosign` on `PATH` | **skipped** (`no image provided` or `cosign not installed`) | non-zero exit |
| `sbom` | `sbom.spdx.json` in project root | n/a (always runs) | **failed** if file missing, invalid JSON, or missing `spdxVersion` |
| `smoke` | `--smoke-url` | **skipped** (`no smoke URL provided`) | HTTP/network error or status ≥ 400 |

Verifier plugins registered under `springdocker.verifiers` run after the built-in checks. See `docs/extensions.md`.

### Skip vs fail semantics

- **skipped** checks do not fail the command. They appear in table/JSON/JUnit/SARIF output for visibility.
- **failed** checks set the overall result to `failed` and make `springdocker verify` exit with code `1`.
- Only **failed** checks affect the exit code. A run where every external tool is missing but `sbom.spdx.json` is valid still exits `0`.

Optional tools are intentionally optional: install `hadolint`, `trivy`, `dive`, and `cosign` locally or in CI when you want those gates enforced.

Supported `--format` values: `table` (default), `json`, `junit`, `sarif`, plus plugin-provided formats.

## Security hardening

See `docs/security-hardening.md` for the runtime hardening defaults and recommended `docker run` flags.

## Binary distribution

See `docs/distribution.md` for packaging notes and sample Homebrew, Scoop, standalone binary, and Docker runtime artifacts.

## Multi-architecture builds

See `docs/multiarch.md` for the Buildx-friendly Dockerfile output and example multi-arch build command.

## Compare command

`springdocker benchmark compare` compares each variant against a required baseline variant and reports deltas.

- `--baseline-variant` selects the variant to compare against.
- `--scenario` narrows the CSV to one scenario.
- `--format json` produces machine-readable deltas.

## Benchmark run reproducibility

`springdocker benchmark run` supports deterministic benchmark controls for local or CI runs:

- `--cpuset-cpus` pins benchmark containers to specific CPUs.
- `--memory` caps container memory.
- `--warmup-runs` executes discarded warmup probes before recording results.
- `--max-workers` runs standard scenarios concurrently with controlled worker count.
- `--normalized-runtime` applies read-only, no-new-privileges, and tmpfs isolation.

These settings can also come from `[benchmark.run]` in `.springdocker.toml`.
