# springdocker positioning

`springdocker` targets the middle ground between black-box image builders and fully hand-written Dockerfiles:

- You get a generated Dockerfile with strong defaults.
- You keep direct ownership of the container definition.
- You can explain (advisory review) and verify (CI gates) the output.

`explain` uses static text heuristics — useful for documentation and PR review, not a security or correctness audit. `verify` runs tool-backed and config checks with pass/fail semantics; use it to block merges. See [cli/README.md](../cli/README.md#explain-command).

This document separates **what the CLI ships and CI validates** from **what the benchmark sample demonstrates** and **what remains roadmap**.

## Target audience

Resolved in [#87](https://github.com/mnafshin/springdocker/issues/87) — see [ADR 0008](adr/0008-target-audience.md).

**Primary: production teams** adopting Spring Boot containerization with a Dockerfile they own, review in PRs, and verify in CI. Install from PyPI; run against your service; use Java 17+ and your Spring Boot version via config.

**Secondary: conference and evidence storytelling.** Presentations, benchmark scenarios, and the reference sample (`Spring Boot 4`, `Java 25`) live in this repository to support reproducible talks and tuning evidence. They are optional — not required for production rollout and not claims about every user's stack. Ownership, update cadence, and publish policy: [`docs/presentation/README.md`](../presentation/README.md).

**Not primary: lab-only research tooling.** Stress-testing happens in-repo; the shipped CLI is general-purpose for real projects.

### Java 25 / Spring Boot 4 in the reference sample (not CLI default)

The benchmark sample uses bleeding-edge versions to exercise generator output and publish evidence. That is intentional for the **secondary** audience. The **CLI** falls back to **Java 17** when the project version is undetected. Production users configure `java_version` and profiles for their own LTS or current JDK — see [adopt.md](adopt.md). The sample version choice is a **feature for evidence depth**, not a requirement for adoption.

## Distribution

**Two install surfaces:**

| Path | Use when |
|---|---|
| `pip install springdocker` / `pipx` / `uv tool` | Full toolkit — Dockerfile, explain, verify, benchmarks; `.springdocker.toml` SSOT ([ADR 0005](adr/0005-config-first-dockerfile-generation.md)) |
| Maven plugin `io.github.mnafshin:springdocker-maven-plugin` | Java-only builder — generate/verify from `pom.xml`; no Python ([ADR 0010](adr/0010-pom-gradle-ssot-java-builder.md)) |
| Clone + `python scripts/checkout_sample.py` | Reproduce benchmark scenarios, reference CSVs, presentation numbers ([`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample)) |
| Clone + editable install | CLI development ([CONTRIBUTING.md](../CONTRIBUTING.md)) |

**PyPI-first** remains the distribution model for the CLI ([ADR 0006](adr/0006-pypi-first-distribution.md)). The Maven plugin is a separate artifact (local `mvn install` today; Maven Central tracked in [#145](https://github.com/mnafshin/springdocker/issues/145)).

The reference sample is a separate repository, pinned from this one. See [ADR 0009](adr/0009-external-sample-repository.md).

## Product scope

springdocker is a **general-purpose CLI** for Maven and Gradle Spring Boot projects:

| In scope today | Out of scope today |
|---|---|
| Project detection, config, Dockerfile generation | Replacing your CI platform or registry |
| `explain` — advisory static analysis for human review | Using `explain` as a security or correctness CI gate |
| `verify` — pass/fail checks for CI (config SSOT, optional hadolint/trivy/…) | Guaranteed native-image production workflow |
| Optional benchmark asset generation, run, and analyze | Universal JVM tuning prescriptions for every workload |
| Plugin hooks for recipes, mutators, and verifiers | Full compatibility matrix across all Spring Boot versions |

The CLI supports **Java 17+** on any Maven/Gradle Spring Boot project. When `java_version` is omitted, springdocker prefers the **detected** project Java, then falls back to **17**. The **reference sample** ([`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample)) stays on Spring Boot 4 / Java 25 to drive benchmark evidence and presentation numbers — that is not a claim that every user must run Java 25.

## Shipped guarantees (CI-evidenced)

These behaviors are enforced by [`.github/workflows/ci.yml`](../.github/workflows/ci.yml):

| Area | What CI proves |
|---|---|
| **CLI quality** | `ruff` lint, `mypy` on `src/`, pytest suites (`unit`, `integration`, `e2e`, `benchmark`) on Ubuntu/macOS/Windows and Python 3.10–3.12 |
| **Package coverage** | ≥80% line coverage on the entire `springdocker` package (same gate as local `pytest`; see `pyproject.toml`) |
| **Dockerfile generation** | Snapshot and e2e tests on `tests/fixtures/{maven-only,gradle-only}` — output shape, flags, and explain/verify wiring |
| **Benchmark generator** | `benchmark-hygiene` checks out the pinned sample, runs `benchmark generate`, and asserts generated assets stay gitignored in the sample repo |
| **Benchmark analyzer** | `benchmark-regression` verifies sample `03-base-image-choice/results/baseline.json` matches analyze output for the paired `raw.csv`, then runs the 20% regression comparator |
| **Docker smoke build** | `docker-smoke` generates a Dockerfile for the pinned sample checkout, runs `docker build`, and probes `/actuator/health/readiness` on port 8081 |
| **Supply chain (repo)** | SPDX SBOM artifact, **blocking** CRITICAL Trivy filesystem scan, and `digest-pins` job verifying registry manifests for `digest_pins.py` |

What CI **does not** prove today:

- Full benchmark suite execution against real Docker on every push.
- `springdocker verify` with hadolint, trivy, dive, or cosign installed — verify tests mock or skip external tools.
- Performance numbers in presentations or docs — those come from local/reference runs on the sample app.

Public docs and talks should treat benchmark tables as **sample evidence**, not fleet-wide guarantees, unless you reproduce them on your project.

## Optional evidence subsystem

Benchmarks are an **opt-in extra** (`pip install springdocker[benchmark]`):

1. `benchmark generate` — writes scenario Dockerfiles locally (gitignored under the sample tree).
2. `benchmark run` — requires Docker on the host; skipped for native scaffold scenarios by default.
3. `benchmark analyze` / `compare` — summarize `raw.csv`; one pinned baseline is gated in CI.

Use benchmarks to **inform** Dockerfile and JVM decisions on your service. They do not replace policy choices (non-root, digest pins, SBOM) or service-specific profiling.

See [`benchmarks.md`](benchmarks.md) and the sample’s [`benchmarks/README.md`](https://github.com/mnafshin/java-spring-docker-sample/blob/main/benchmarks/README.md) for artifact policy.

## Sample project strategy (two trees)

CLI onboarding/regression stays in this repository; evidence depth lives in an external sample:

| Path | Audience | Validated in CI |
|---|---|---|
| `tests/fixtures/{maven-only,gradle-only}/` | Humans learning the CLI and automated regression | unit, integration, e2e, benchmark tests |
| [`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample) → `samples/java-spring-docker/` | Benchmark harness and reference evidence | generator hygiene + analyzer regression on pinned CSV + `docker-smoke` build/readiness |

Fixtures are minimal (CLI/output shape only). Full Docker builds and presentation numbers use the external sample (checked out under `samples/`). Do not copy the full benchmark tree into every consumer repo.

Resolved in [#95](https://github.com/mnafshin/springdocker/issues/95) / ADR 0004; externalization in [ADR 0009](adr/0009-external-sample-repository.md).

## Reference stack vs compatibility

| Layer | CLI / production path | Reference sample (evidence) |
|---|---|---|
| Spring Boot | Maven/Gradle projects with Spring Boot markers | 4.0.1 sample app |
| Java | Floor **17**; init/undetected fallback **17**; JEP 483 AOT **24+** | **25** in sample `.springdocker.toml` (includes scenario 02) |
| Python CLI | Requires Python ≥3.10 | 3.12 in CI |

Feature matrix and support ranges: [jvm.md](jvm.md).

Production teams set `java_version` in `.springdocker.toml` for their service. The reference sample stays on current JDK/Spring Boot for benchmark and presentation refresh — see [ADR 0008](adr/0008-target-audience.md).

## Why not Jib?

Jib is excellent when you want fast Java image builds without writing Dockerfiles.  
The tradeoff is reduced direct control over the final Dockerfile-level shape.

Choose Jib when:
- your team wants minimal container-layer customization
- Dockerfile ownership is not required

Choose springdocker when:
- your team wants a real Dockerfile artifact in-repo
- you need explicit, reviewable container decisions

## Why not Buildpacks / Paketo / `spring-boot:build-image`?

Buildpacks are great for zero-configuration builds and ecosystem integration.  
The tradeoff is an opinionated build pipeline that can feel opaque when debugging image-level behavior.

Choose Buildpacks when:
- platform defaults are enough
- your team is comfortable with buildpack internals and lifecycle behavior

Choose springdocker when:
- you need explicit Dockerfile ownership
- you want explainable, reviewable Dockerfile output as a first-class artifact

## Why not hand-written Dockerfiles?

Hand-written Dockerfiles maximize control and flexibility, but they are easy to drift and costly to keep aligned with evolving best practices.

Choose hand-written Dockerfiles when:
- your image has highly custom constraints that generators cannot model

Choose springdocker when:
- you want a maintainable baseline generated from repeatable conventions
- you still want manual control after generation

## Summary

springdocker is for teams that want:

1. a Dockerfile they can own and edit
2. opinionated defaults for Spring Boot containerization
3. explain-and-verify workflows around the generated output
4. optional, reproducible benchmark evidence — not a black-box image builder

## Review backlog

Scope-vs-polish gaps called out in the repository review (native scaffold, benchmark hygiene, CI smoke builds, sample-tree consolidation, and more) are tracked in the [**Review backlog** milestone](https://github.com/mnafshin/springdocker/milestone/1). Prefer closing those items before expanding public guarantees.
