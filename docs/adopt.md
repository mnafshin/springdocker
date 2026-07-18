# Adopt springdocker (config-first)

Install from PyPI and run against **your** Spring Boot service. Clone this repo only for benchmarks, presentations, or contributions.

Related: [ADR 0005](adr/0005-config-first-dockerfile-generation.md) · [CLI config-first](../cli/README.md#config-first-workflow) · [POSITIONING](POSITIONING.md)

## Mental model

| Artifact | Role |
|---|---|
| `.springdocker.toml` | **Strategy** — reviewable decisions (runtime, jlink, JVM flags, SBOM, …) |
| `Dockerfile.generated` | **Output** — deterministic artifact from config |
| `springdocker configure` | Interactive onboarding that **writes config** |
| `springdocker dockerfile generate` | Non-interactive generation for local use and CI |

Precedence: `CLI flags > .springdocker.toml > built-in defaults`.

Set `java_version` to your toolchain (**17+**). Undetected fallback is **17**. JEP 483 AOT requires **24+** — see [jvm.md](jvm.md).

## Quickstart

```bash
pipx install springdocker
cd /path/to/your-spring-boot-app
springdocker doctor --project-root .
springdocker init --project-root . --build-tool maven
springdocker configure --project-root . --force
springdocker dockerfile generate --project-root .
springdocker verify --project-root . --dockerfile Dockerfile.generated --check-config-drift
```

Or: `springdocker init --project-root . --build-tool maven --interactive`.

Platform teams can seed config from the sample’s [`.springdocker.toml`](https://github.com/mnafshin/java-spring-docker-sample/blob/main/.springdocker.toml).

### Contributor / evidence (clone)

```bash
python3 -m pip install -e ".[dev]"   # or springdocker[benchmark] for evidence runs
python scripts/checkout_sample.py    # fixtures → CLI regression; sample → benchmarks (Java 25)
```

## Daily workflow

After config exists: `springdocker dockerfile generate --project-root .`

Permanent strategy changes: edit `.springdocker.toml` or `springdocker configure --force`.

Advisory audit: `springdocker explain Dockerfile.generated --format json --config-aware`  
CI gate: `springdocker verify --check-config-drift` (below).

### PR checklist

- `[dockerfile]` diffs explain **why**
- Regenerated Dockerfile matches config intent
- Distroless: orchestrator readiness probe (no Dockerfile `HEALTHCHECK`) — see [cli README](../cli/README.md#runtime-bases-and-healthcheck) and [sample k8s](https://github.com/mnafshin/java-spring-docker-sample/tree/main/k8s)

## CI pipeline

```yaml
# .github/workflows/dockerfile.yml
name: Dockerfile SSOT
on: [pull_request, push]
jobs:
  dockerfile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: python3 -m pip install springdocker
      - run: springdocker dockerfile generate --project-root .
      - run: springdocker verify --project-root . --dockerfile Dockerfile.generated --check-config-drift --format json
```

Ensure `sbom.spdx.json` exists when `include_embedded_sbom = true`.

## Profiles

| Profile | Best for |
|---|---|
| `production-balanced` | Team default — distroless + jlink + supply chain |
| `smallest-image` | alpine + jlink |
| `fast-cold-start` | Java 24+: JEP 483 AOT; 17–23: AppCDS |
| `build-speed` | debian-slim, no jlink |
| `simplest` | temurin fat JAR |
| `compliance` | SBOM, pins, OCI labels, reproducible controls |
| `custom` | Wizard asks each option |

Overlays: `src/springdocker/dockerfile_profiles.py`. JVM flags: [jvm.md](jvm.md).

## Platform playbook

1. Publish an org golden `.springdocker.toml`
2. CI with `--check-config-drift` on PRs
3. Document allowed one-off CLI overrides
4. Optional later: org policy overlay ([#123](https://github.com/mnafshin/springdocker/issues/123))

## FAQ

**Commit Dockerfile, config, or both?** Prefer both when pipelines/reviewers consume the Dockerfile. Use `--check-config-drift` or `git diff` in CI.

**Java upgrades:** bump `java_version` → generate → review digests → re-test. Scenario 02 (AOT) only when Java ≥ 24.

**No HEALTHCHECK on distroless?** No shell — use Kubernetes probes ([sample k8s](https://github.com/mnafshin/java-spring-docker-sample/tree/main/k8s)).

**Hand-edit Dockerfile?** Temporary only; drift checks will fail until config catches up.

**jlink modules:** `must_have_modules_file` plus optional Web baseline — see [cli README](../cli/README.md) / ADR 0007.

## Migrations

| Legacy | Replacement |
|---|---|
| `tools/dockerfile_wizard.py` | `springdocker configure` + `dockerfile generate` |
| `legacy_scripts` / `--use-legacy-scripts` | Internal runner (default); removed in v2.0.0 |

## Benchmarks

Optional evidence — [benchmarks.md](benchmarks.md). Reproduce on the sample with Java **25**; on your 17–23 service, scenario 02 is omitted.
