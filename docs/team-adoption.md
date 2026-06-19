# Team adoption guide: config-first Dockerfile workflow

This guide explains how teams adopt **springdocker** with `.springdocker.toml` as the single source of truth (SSOT) for Dockerfile generation.

Related design docs:

- [Epic #113](https://github.com/mnafshin/springdocker/issues/113) — config-first Dockerfile workflow
- [ADR 0005: Config-first Dockerfile generation](adr/0005-config-first-dockerfile-generation.md)
- [CLI reference](../cli/README.md#config-first-workflow)

## Mental model

| Artifact | Role |
|---|---|
| `.springdocker.toml` | **Strategy** — reviewable, versioned decisions (runtime base, jlink, JVM flags, SBOM, …) |
| `Dockerfile.generated` | **Output** — deterministic artifact produced from config |
| `springdocker configure` | Interactive onboarding that **writes config** |
| `springdocker dockerfile generate` | Non-interactive generation for local use and CI |

Do not treat the Dockerfile as the place to encode policy. Change config, regenerate, and review the diff.

Precedence when generating:

```
CLI flags  >  project .springdocker.toml  >  built-in defaults
```

Org-wide policy overlay (`SPRINGDOCKER_POLICY`) is planned in [#123](https://github.com/mnafshin/springdocker/issues/123) and is not required for team rollout today.

## First-time setup (one developer or platform seed)

### Option A — skeleton + wizard (recommended)

```bash
cd your-service/
springdocker init --project-root . --build-tool maven
springdocker configure --project-root . --force
git add .springdocker.toml
git commit -m "Add springdocker Dockerfile strategy"
springdocker dockerfile generate --project-root .
git add Dockerfile.generated
git commit -m "Generate Dockerfile from config"
```

`init --interactive` combines the skeleton and wizard:

```bash
springdocker init --project-root . --build-tool maven --interactive
```

### Option B — copy a golden template

Platform teams can maintain a starter `.springdocker.toml` (see [samples/java-spring-docker/.springdocker.toml](../samples/java-spring-docker/.springdocker.toml)) and ask services to copy it, then run `configure` or edit keys directly.

### PR review checklist

- `[dockerfile]` changes explain **why** (runtime, security, startup tradeoffs).
- Regenerated Dockerfile diff matches the config intent.
- `springdocker explain --config-aware` shows no drift when auditing locally.
- Distroless runtime: confirm Kubernetes `readinessProbe` replaces Dockerfile `HEALTHCHECK` (see [cli/README.md](../cli/README.md#runtime-bases-and-healthcheck)).

## Daily developer workflow

After config exists, developers usually only run:

```bash
springdocker dockerfile generate --project-root .
```

Use CLI overrides for one-off experiments (not committed):

```bash
springdocker dockerfile generate --runtime-image alpine --no-use-jlink
```

To change strategy permanently, edit `.springdocker.toml` or rerun `springdocker configure --force`.

Inspect what the generator decided:

```bash
springdocker explain Dockerfile.generated --format json --config-aware
```

## CI pipeline (copy-pasteable)

Non-interactive generate, config drift verification, and optional external gates:

```yaml
# .github/workflows/dockerfile.yml
name: Dockerfile SSOT

on:
  pull_request:
  push:
    branches: [main]

jobs:
  dockerfile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install springdocker
        run: python3 -m pip install springdocker

      - name: Generate Dockerfile from config
        run: springdocker dockerfile generate --project-root .

      - name: Verify config SSOT (drift, SBOM, non-root, JVM flags)
        run: springdocker verify --project-root . --dockerfile Dockerfile.generated --check-config-drift --format json

      - name: Explain with config audit (optional JSON artifact)
        run: springdocker explain --project-root . Dockerfile.generated --format json --config-aware > explain.json

      # Optional: commit Dockerfile.generated in repo and fail on uncommitted drift:
      # - run: git diff --exit-code Dockerfile.generated
```

Minimal shell equivalent:

```bash
set -euo pipefail
springdocker dockerfile generate --project-root .
springdocker verify --project-root . --dockerfile Dockerfile.generated --check-config-drift
```

Ensure `sbom.spdx.json` exists in the project root when `include_embedded_sbom = true` — `verify` checks the project SBOM file and the Dockerfile embed path.

## Platform team playbook

Today (without org policy):

1. Publish a **golden** `.springdocker.toml` for your org (profile + explicit keys).
2. Add CI with `--check-config-drift` on every PR touching config or Dockerfile.
3. Document allowed CLI override dimensions for experiments (runtime base, JVM flags).
4. Use `springdocker init --interactive` in service templates.

Planned ([#123](https://github.com/mnafshin/springdocker/issues/123)):

- `SPRINGDOCKER_POLICY` TOML with org defaults and `locked` keys teams cannot weaken.
- `verify` assertions for locked policy compliance.

## Profile presets

Selected in `springdocker configure`; saved as explicit `[dockerfile]` keys (plus optional `profile = "…"` metadata).

| Profile | Best for | Highlights |
|---|---|---|
| `production-balanced` | Default team standard | distroless + jlink + SBOM + digest pins + tuned JVM |
| `smallest-image` | Minimum image size | alpine + jlink; AppCDS off |
| `fast-cold-start` | Startup latency (Java 24+) | distroless + jlink + JEP 483 AOT cache |
| `build-speed` | Faster image builds in dev | debian-slim, no jlink |
| `simplest` | Onboarding / debugging | temurin JRE fat JAR, no jlink/layers |
| `compliance` | Supply-chain heavy environments | SBOM, pins, OCI labels, reproducible controls |
| `custom` | Full control | wizard asks each option individually |

See `src/springdocker/dockerfile_profiles.py` for the exact option overlays.

## JVM flags

When `tuned_jvm_flags = true` and `jvm_flags` is unset, the generator applies:

- `-XX:MaxRAMPercentage=75`
- `-XX:+ExitOnOutOfMemoryError`
- `-Djava.io.tmpdir=/tmp`

To override entirely, set an explicit list:

```toml
[dockerfile]
tuned_jvm_flags = false
jvm_flags = ["-XX:+UseZGC", "-XX:MaxRAMPercentage=70"]
```

CLI equivalent: repeatable `--jvm-flag=-XX:+UseZGC` (use `=` form when the flag starts with `-`).

More background: [jvm-optimization.md](jvm-optimization.md).

## Benchmark relationship

Benchmarks are **optional evidence**, not a gate for `dockerfile generate`.

| Use benchmark when… | Skip benchmark when… |
|---|---|
| Comparing runtime bases or startup optimizations | You only need a standard production Dockerfile |
| Publishing regression baselines for CI | Local dev iteration on config keys |
| Validating a JVM flag change with data | Time-to-ship is dominated by app changes |

Commands: `benchmark generate`, `benchmark run`, `benchmark analyze` — see [benchmark-methodology.md](benchmark-methodology.md).

## Migration from legacy `tools/dockerfile_wizard.py`

The sample script `tools/dockerfile_wizard.py` is **retired**. It now prints migration guidance and exits.

| Legacy | Config-first replacement |
|---|---|
| `python3 tools/dockerfile_wizard.py --interactive` | `springdocker configure` |
| Wizard flags / profiles | `[dockerfile]` keys or `configure` profile |
| Script output Dockerfile | `springdocker dockerfile generate` |

Map common wizard choices:

- **Balanced profile** → `production-balanced` in `configure`, or copy sample config.
- **Native / AOT experiments** → `recipe = "spring-aot"` or scaffold `native-aot` (see [native-image-roadmap.md](native-image-roadmap.md)).
- **Runtime base** → `runtime_image` in config (`distroless`, `alpine`, `debian-slim`, …).

## FAQ

### Should we commit `Dockerfile.generated` or only `.springdocker.toml`?

**Prefer committing both** when downstream pipelines consume the Dockerfile directly (build systems, security scanners, reviewers who do not run springdocker). CI can regenerate and fail on drift with `--check-config-drift` or `git diff`.

Config-only repos work if every environment runs `dockerfile generate` before build — document that requirement.

### How do Java upgrades work with Renovate or manual bumps?

1. Update `java_version` in `[dockerfile]` (and `[benchmark.generate]` if used).
2. Run `springdocker dockerfile generate`.
3. Review digest-pinned base images in the regenerated Dockerfile.
4. Re-run tests and optional benchmarks.

### Why is there no `HEALTHCHECK` with distroless?

Distroless images have no shell. Use orchestrator probes — see [kubernetes.md](kubernetes.md) and the sample under `samples/java-spring-docker/k8s/`.

Set `healthcheck_path` in config for OS-based runtimes; omit or use auto-detect for actuator on full OS images.

### Can developers edit the Dockerfile by hand?

Yes for emergencies, but CI `--check-config-drift` will fail until config is updated or the file is regenerated. Treat hand-edits as temporary.

### Where do must-have jlink modules go?

List modules in a file (e.g. `must-have.txt`) and set `must_have_modules_file` in config. Baseline modules (`java.desktop`, `java.logging`, `java.naming`) are merged automatically unless disabled via `jlink_baseline_modules = []`.

## Sample project

The benchmark sample at [samples/java-spring-docker/](../samples/java-spring-docker/) includes a full exemplar `.springdocker.toml` and a [team workflow section](../samples/java-spring-docker/README.md#config-first-team-workflow).
