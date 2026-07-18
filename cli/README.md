# springdocker CLI

CLI for Spring Boot Dockerfile and benchmark workflows across Maven and Gradle projects.

Product scope and CI-evidenced guarantees: [`docs/POSITIONING.md`](../docs/POSITIONING.md).

## Install

**Primary path:** install from PyPI and run against your Spring Boot project. Clone the repository only for benchmarks on the sample app or for development ([ADR 0006](../docs/adr/0006-pypi-first-distribution.md)).

### pipx (recommended)

```bash
pipx install springdocker
springdocker --help

# optional: benchmark run/analyze (requires Docker)
pipx install 'springdocker[benchmark]'
```

Upgrade:

```bash
pipx upgrade springdocker
```

### uv

```bash
uv tool install springdocker
uv tool upgrade springdocker

# benchmark extra
uv tool install 'springdocker[benchmark]'
```

### pip

```bash
python3 -m pip install springdocker
python3 -m pip install 'springdocker[benchmark]'
```

### From source (contributors)

```bash
git clone https://github.com/mnafshin/springdocker.git
cd springdocker
python3 -m pip install -e ".[dev]"
```

## Quick usage

```bash
cd /path/to/your-spring-boot-app   # or: export PROJECT=.
springdocker setup --ci
# optional: springdocker setup --verify
# existing project: springdocker setup --ci-only
# interactive: springdocker setup --interactive

# power-user / CI steps (same result as setup without --ci)
springdocker doctor --project-root .
springdocker init --project-root . --build-tool maven
springdocker configure --project-root . --force
springdocker dockerfile generate --project-root .
springdocker explain --project-root . Dockerfile.generated --format json --config-aware
springdocker verify --project-root . --dockerfile Dockerfile.generated --check-config-drift

# recipes
springdocker dockerfile generate --project-root . --recipe jvm-balanced
springdocker dockerfile generate --project-root . --recipe spring-aot
# native-aot is experimental scaffold only — see docs/native-aot.md
springdocker dockerfile generate --project-root . --recipe native-aot
```

**Evidence on the sample app** ([`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample); Java 25) — from a springdocker clone:

```bash
python scripts/checkout_sample.py
springdocker benchmark generate --project-root samples/java-spring-docker --java-version 25
springdocker benchmark run --project-root samples/java-spring-docker --profile quick --runner-arg --skip-native
springdocker benchmark analyze --project-root samples/java-spring-docker \
  samples/java-spring-docker/benchmarks/01-custom-jre-jlink/results/raw.csv --format table
```

Scenario index and methodology: [docs/benchmarks.md](../docs/benchmarks.md#scenario-index).
CI regression baseline example: sample `benchmarks/03-base-image-choice/results/baseline.json` (pinned via `scripts/java_spring_docker_sample.manifest.json`).

## Dockerfile recipes

| Recipe | Status | Default runtime | Notes |
|---|---|---|---|
| `jvm-balanced` | Supported | **distroless** + jlink | Default production-oriented JVM Dockerfile. |
| `spring-aot` | Supported | **distroless** + jlink | Spring Boot AOT processing on a JVM runtime. |
| `native-aot` | Scaffold only | **distroless** base (static binary) | Experimental GraalVM native-image Dockerfile. Not production-ready — [docs/native-aot.md](../docs/native-aot.md). |

The generator sets `runtime_image = "distroless"` internally for JVM recipes. That means `distroless/base-debian*` plus a copied jlink runtime — not the prebuilt `distroless/java*` image and not a full OS layer unless you change generator options (benchmark scenario **03** compares OS bases).

### Runtime bases and HEALTHCHECK

| Runtime | Generator behavior |
|---|---|
| `distroless` (default) | Non-root, minimal base + jlink; **no `HEALTHCHECK`** (no shell/`wget` in the image). Probe readiness from the orchestrator (e.g. Kubernetes `readinessProbe` on `/actuator/health/readiness`). |
| `debian-slim`, `alpine`, `ubuntu`, `temurin` | Full OS or vendor JRE paths; **`HEALTHCHECK` is emitted** when Spring Boot Actuator is on the classpath. |

Supported runtime names: `distroless`, `debian-slim`, `alpine`, `ubuntu`, `temurin` (plus aliases such as `debian-bookworm-slim`, `eclipse-temurin-jre`). Set via `[dockerfile].runtime_image` in `.springdocker.toml` or `--runtime-image` on `dockerfile generate`.

## Config-first workflow

`.springdocker.toml` is the **single source of truth** for Dockerfile generation (see [ADR 0005](../docs/adr/0005-config-first-dockerfile-generation.md)). Team rollout: [docs/adopt.md](../docs/adopt.md).

### Command matrix

| Command | Interactive? | Writes config? | Writes Dockerfile? | Typical user |
|---|---|---|---|---|
| `springdocker setup` | No (optional `--interactive`) | Yes (`production-balanced` by default) | Yes | First-time onboarding (`--ci` writes GitHub workflow) |
| `springdocker setup --ci-only` | No | No | No (writes workflow) | Add SSOT gate to an existing service |
| `springdocker init` | No | Yes (skeleton) | No | Platform / first checkout |
| `springdocker init --interactive` | Yes (via configure) | Yes | No | New service bootstrap |
| `springdocker configure` | Yes | Yes (`[dockerfile]`) | Optional (`--generate`) | Strategy changes |
| `springdocker dockerfile generate` | No | No | Yes | Daily dev + CI |
| `springdocker explain --config-aware` | No | No | No | Audit / review (advisory — not a CI gate) |
| `springdocker verify --check-config-drift` | No | No | No | CI SSOT gate (pass/fail) |

### Precedence

| Priority | Source |
|---:|---|
| 1 | CLI flags on `dockerfile generate` |
| 2 | Project `.springdocker.toml` |
| 3 | Built-in defaults |

Org policy (`SPRINGDOCKER_POLICY`) is planned ([#123](https://github.com/mnafshin/springdocker/issues/123)); not required today.

| Command | Purpose |
|---|---|
| `springdocker setup` | One-shot detect → write config → generate Dockerfile (`--ci` adds GitHub Action workflow) |
| `springdocker setup --ci-only` | Write `.github/workflows/dockerfile.yml` only |
| `springdocker configure` | Interactive wizard that writes/updates `[dockerfile]` in config |
| `springdocker init --interactive` | Create config skeleton, then run configure |
| `springdocker dockerfile generate` | Deterministic generate from config (CI-safe, no prompts) |

Profiles (`production-balanced`, `smallest-image`, `fast-cold-start`, `build-speed`, `simplest`, `compliance`, `custom`) are selected in `setup --profile` / `configure` and expanded to explicit options in config.

### `dockerfile generate` CLI overrides

Every `[dockerfile]` key is overridable from the CLI except file-backed keys (`must_have_modules_file`, `jlink_baseline_modules`), which stay in config only.

| Section | CLI flags | Config key(s) |
|---|---|---|
| General | `--output`, `--java-version`, `--recipe`, `--profile` | `output`, `java_version`, `recipe`, `profile` |
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

The `04-native-benchmark` scenario is generated with the `native-aot` scaffold recipe. The internal benchmark runner skips native scenarios by default (`--skip-native`).

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
java_version = 17
recipe = "jvm-balanced"
# profile = "production-balanced"  # set by `springdocker configure`
# runtime_image = "distroless"
# use_jlink = true
# enable_appcds = true  # available on Java 17+
# enable_jep483_aot_cache = false  # requires Java 24+; mutually exclusive with AppCDS
# include_embedded_sbom = true
# pin_digests = true
# tuned_jvm_flags = true
# jvm_flags = ["-XX:MaxRAMPercentage=75", "-XX:+ExitOnOutOfMemoryError", "-Djava.io.tmpdir=/tmp"]
# Generator default runtime: distroless (gcr.io/distroless/base-* + jlink + layered JAR).
# Set java_version to your service toolchain (17+). Sample evidence project uses 25.
must_have_modules_file = "must-have.txt"

[benchmark.generate]
java_version = 17
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

When jlink is enabled, springdocker auto-merges **jlink baseline modules** when Spring Web starters
are detected (`spring-boot-starter-web`, `spring-boot-starter-webflux`, `spring-boot-starter-websocket`):

- `java.desktop` — JavaBeans and desktop-related APIs used by parts of the Spring Web stack
- `java.logging` — `java.util.logging` used by framework and library code
- `java.naming` — JNDI lookups that jdeps often misses on web apps

Non-web Spring Boot workloads get **no** auto baseline — use jdeps plus `must_have_modules_file` for
extra modules. Override or disable in `.springdocker.toml`:

```toml
[dockerfile]
# Omit jlink_baseline_modules to auto-detect from Spring Web starters at generate time.
# Override defaults or set [] to disable baseline injection.
jlink_baseline_modules = ["java.desktop", "java.logging", "java.naming"]
```

See [ADR 0007](../docs/adr/0007-jlink-baseline-modules-web-detection.md).

`springdocker explain` reports baseline and curated modules separately in JSON/table output.
Baseline modules are generator defaults; curated modules come from `must_have_modules_file`.

Create template config:

```bash
springdocker init --project-root samples/java-spring-docker --build-tool gradle
springdocker init --project-root samples/java-spring-docker --build-tool gradle --profile full --print
```

### `init --interactive`

Creates `.springdocker.toml` if missing, then runs the same wizard as `configure` (no Dockerfile write unless you chain commands yourself):

```bash
springdocker init --project-root . --build-tool maven --interactive
# equivalent to:
# springdocker init --project-root . --build-tool maven
# springdocker configure --project-root . --force
```

Use `--force` on `init` to overwrite an existing skeleton; use `configure --force` to replace only the `[dockerfile]` section in an existing file.

See [docs/adopt.md](../docs/adopt.md) for first-time setup, CI examples, and migration from the retired `tools/dockerfile_wizard.py`.

## Legacy benchmark scripts (deprecated)

`benchmark generate` and `benchmark run` still accept `--use-legacy-scripts`, `SPRINGDOCKER_LEGACY_SCRIPTS=1`, or `legacy_scripts = true` in `.springdocker.toml` to delegate to project scripts under `benchmarks/`. **This path is deprecated and will be removed in v2.0.0.** The CLI prints a warning when legacy mode is used.

Migrate by removing legacy flags and config keys — the internal implementation is the default:

```bash
springdocker benchmark generate --project-root .
springdocker benchmark run --project-root .
```

Dockerfile generation always uses the internal config-driven generator. Use `springdocker configure` for interactive setup instead of the retired `tools/dockerfile_wizard.py` script.

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

`springdocker explain` reads a Dockerfile and **describes** optimizations it recognizes using static text heuristics (regex and keyword matching).

**Advisory only — not a CI gate.** Explain output helps humans review and document a Dockerfile. It does **not** perform a security audit, lint the file, scan images, or prove runtime correctness. Hand-written Dockerfiles may be misread; a missing feature in explain output does not mean that optimization is absent at runtime.

**Use `springdocker verify` for CI gates** — hadolint, trivy, SBOM checks, optional dive/cosign/smoke, and `--check-config-drift` for config SSOT compliance. Only `verify` uses pass/fail semantics suitable for blocking merges.

Recognized signals include:

- multi-stage layout
- BuildKit cache usage
- jlink runtime stage
- non-root runtime
- tuned JVM flags
- jlink baseline modules (built-in defaults)
- curated must-have modules (from `must-have.txt`)

Use `--format json` when you want stable structured output. The JSON `notes` field repeats the advisory scope and points to `verify`.

Add `--config-aware` to include resolved `[dockerfile]` options from `.springdocker.toml`, per-option sources (`default` or `project`), and drift detection against `dockerfile generate`. Config drift in explain is informational; enforce SSOT in CI with `verify --check-config-drift`:

```bash
springdocker explain --project-root . Dockerfile.generated --format json --config-aware
springdocker verify --project-root . --dockerfile Dockerfile.generated --check-config-drift
```

## Verify command

`springdocker verify` runs a battery of checks against a generated Dockerfile and optional runtime context. It is designed to work in CI without installing every external tool.

```bash
springdocker verify --project-root tests/fixtures/maven-only Dockerfile.generated
springdocker verify --project-root tests/fixtures/maven-only Dockerfile.generated \
  --image demo:latest \
  --smoke-url http://127.0.0.1:8081/actuator/health \
  --format junit \
  --output reports/verify.junit.xml
springdocker verify --project-root . --dockerfile Dockerfile.generated --check-config-drift
springdocker verify --project-root . --dockerfile nested/Dockerfile.generated --trivy-scan-project-root
```

By default, `trivy` scans the Dockerfile path and the directory that contains it (the Docker build context). On monorepos with nested Dockerfiles, this avoids scanning unrelated modules. Pass `--trivy-scan-project-root` to restore the previous full-tree scan.

`--check-config-drift` adds config SSOT checks when `.springdocker.toml` is present:

| Check | Validates |
|---|---|
| `config-drift` | Dockerfile matches `dockerfile generate` output for current config |
| `config-embedded-sbom` | `/usr/share/sbom/spdx.json` present when `include_embedded_sbom = true` |
| `config-non-root` | unprivileged `USER` when `non_root = true` |
| `config-jvm-flags` | configured JVM flags appear in `ENTRYPOINT` |

### Built-in checks

| Check | Requires | Missing prerequisite | Check failure |
|---|---|---|---|
| `hadolint` | `hadolint` on `PATH` | **skipped** (`hadolint not installed`) | non-zero exit |
| `trivy` | `trivy` on `PATH` | **skipped** (`trivy not installed`) | HIGH/CRITICAL findings in scanned paths (default: Dockerfile + its directory; use `--trivy-scan-project-root` for full tree) |
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

## Security

See [docs/security.md](../docs/security.md) for runtime hardening and digest-pin rotation.

## Multi-architecture builds

Generated Dockerfiles are Buildx-friendly: `ARG TARGETPLATFORM` / `BUILDPLATFORM`, build stages on `$BUILDPLATFORM`, runtime on `$TARGETPLATFORM`.

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t app:multiarch .
```

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
