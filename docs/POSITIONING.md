# springdocker positioning

`springdocker` targets the middle ground between black-box image builders and fully hand-written Dockerfiles:

- You get a generated Dockerfile with strong defaults.
- You keep direct ownership of the container definition.
- You can explain and verify the output in CI.

This document separates **what the CLI ships and CI validates** from **what the benchmark sample demonstrates** and **what remains roadmap**.

## Product scope

springdocker is a **general-purpose CLI** for Maven and Gradle Spring Boot projects:

| In scope today | Out of scope today |
|---|---|
| Project detection, config, Dockerfile generation | Replacing your CI platform or registry |
| `explain` / `verify` workflows around generated Dockerfiles | Guaranteed native-image production workflow |
| Optional benchmark asset generation, run, and analyze | Universal JVM tuning prescriptions for every workload |
| Plugin hooks for recipes, mutators, and verifiers | Full compatibility matrix across all Spring Boot versions |

The CLI defaults and docs use a **reference sample** (Spring Boot 4, Java 25 under `samples/java-spring-docker/`). That sample drives benchmark evidence and presentation numbers. It is not a claim that every user must run Java 25 or Spring Boot 4 — the generator supports Java 17+ and works against minimal Maven/Gradle fixtures in CI.

## Shipped guarantees (CI-evidenced)

These behaviors are enforced by [`.github/workflows/ci.yml`](../.github/workflows/ci.yml):

| Area | What CI proves |
|---|---|
| **CLI quality** | `ruff` lint, `mypy` on `src/`, pytest suites (`unit`, `integration`, `e2e`, `benchmark`) on Ubuntu/macOS/Windows and Python 3.10–3.12 |
| **Package coverage** | ≥80% line coverage on the entire `springdocker` package (same gate as local `pytest`; see `pyproject.toml`) |
| **Dockerfile generation** | Snapshot and e2e tests on `tests/fixtures/{maven-only,gradle-only}` — output shape, flags, and explain/verify wiring |
| **Benchmark generator** | `benchmark-hygiene` runs `benchmark generate` and asserts generated assets stay gitignored |
| **Benchmark analyzer** | `benchmark-regression` verifies committed `06-base-image-choice/results/baseline.json` matches analyze output for the paired `raw.csv`, then runs the 20% regression comparator |
| **Docker smoke build** | `docker-smoke` generates a Dockerfile for `samples/java-spring-docker`, runs `docker build`, and probes `/actuator/health/readiness` on port 8081 |
| **Supply chain (repo)** | SPDX SBOM artifact, CRITICAL filesystem scan, and `digest-pins` job verifying registry manifests for `digest_pins.py` |

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

See [`benchmark-methodology.md`](benchmark-methodology.md) and [`samples/java-spring-docker/benchmarks/README.md`](../samples/java-spring-docker/benchmarks/README.md) for artifact policy.

## Sample project strategy (two trees)

The repository keeps two Spring Boot paths. They are not two products — they split **CLI onboarding/regression** from **evidence depth**:

| Path | Audience | Validated in CI |
|---|---|---|
| `tests/fixtures/{maven-only,gradle-only}/` | Humans learning the CLI and automated regression | unit, integration, e2e, benchmark tests |
| `samples/java-spring-docker/` | Benchmark harness and reference evidence | generator hygiene + analyzer regression on pinned CSV + `docker-smoke` build/readiness |

**Start with `tests/fixtures/…`** for Dockerfile workflows. Use **`samples/`** when you need benchmark scenarios or reference datasets. Do not copy the full benchmark tree into every consumer repo.

Resolved in [#95](https://github.com/mnafshin/springdocker/issues/95) — see [`docs/decisions/95-sample-project-strategy.md`](decisions/95-sample-project-strategy.md).

## Reference stack vs compatibility

| Layer | Reference (sample/docs) | Broader support |
|---|---|---|
| Spring Boot | 4.0.1 sample app | Maven/Gradle projects with Spring Boot markers; no version matrix published yet ([`compatibility-matrix.md`](compatibility-matrix.md) is roadmap) |
| Java (generated Dockerfiles) | 25 in sample config | Generator requires Java ≥17 |
| Python CLI | 3.12 in CI | Requires Python ≥3.10 |

Revisit whether Java 25 / Spring Boot 4 defaults suit a general audience: [#69](https://github.com/mnafshin/springdocker/issues/69).

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
