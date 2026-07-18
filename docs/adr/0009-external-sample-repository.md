# ADR 0009: External sample repository

## Status

Accepted

## Context

ADR 0004 kept `samples/java-spring-docker/` in this repository as the permanent benchmark harness. That tree is a full Spring Boot 4 / Java 25 application with its own Maven/Gradle identity (`io.github.mnafshin:java-spring-docker`), benchmark CSVs, and k8s overlays. It has a different release cadence and reuse surface than the installable `springdocker` CLI.

ADR 0004 already noted that extracting the workload to a separate repository could be revisited later.

## Decision

1. Move the benchmark sample to a dedicated public repository: [`mnafshin/java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample).
2. Keep `tests/fixtures/{maven-only,gradle-only,…}/` in this repository as the minimal CLI / e2e targets.
3. Pin the sample with [`scripts/java_spring_docker_sample.manifest.json`](../../scripts/java_spring_docker_sample.manifest.json) and check it out via [`scripts/checkout_sample.py`](../../scripts/checkout_sample.py) into gitignored `samples/java-spring-docker/` (same path used by docs and CI commands).
4. CI jobs that need the full app (`benchmark-hygiene`, `benchmark-regression`, `docker-smoke`, coverage, and the `benchmark` test suite) run the checkout script before use.

Local contributors may keep a sibling clone at `../java-spring-docker-sample` or set `JAVA_SPRING_DOCKER_SAMPLE_ROOT`; the checkout script prefers those over cloning.

## Consequences

- This repository stays focused on the CLI package; the sample can be reused for demos and other tooling.
- Cross-repo pin bumps are required when sample baselines or smoke-relevant app code change.
- Until the sample repository is public at the pinned ref, remote CI checkout fails — push `java-spring-docker-sample` before relying on GitHub Actions for sample-backed jobs.

## Non-goals

- Changing Petclinic consumer-smoke (already an external pin).
- Moving `docs/examples/` static snippets into the sample repository.
