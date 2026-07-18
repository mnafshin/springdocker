# ADR 0004: Sample project strategy

## Status

Superseded by [ADR 0009: External sample repository](0009-external-sample-repository.md) for the full benchmark harness location. Fixture strategy below remains in effect.

## Context

The repository had three Spring Boot trees with overlapping roles:

| Path | Former role |
|---|---|
| `examples/spring-boot-{maven,gradle}/` | Human CLI walkthroughs |
| `tests/fixtures/{maven-only,gradle-only}/` | Minimal CI regression targets |
| `samples/java-spring-docker/` | Benchmark harness and versioned evidence |

Maintaining separate walkthrough copies under `examples/` duplicated the minimal Maven/Gradle fixtures already used in CI.

## Decision

1. **Remove** the root `examples/` walkthrough projects.
2. **Keep** `tests/fixtures/{maven-only,gradle-only}/` as the single minimal entry point for Dockerfile CLI workflows (README quick start and e2e coverage).
3. ~~**Keep** `samples/java-spring-docker/` as the permanent in-tree benchmark harness~~ → **moved** to [`mnafshin/java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample) (ADR 0009). Checkout path remains `samples/java-spring-docker/` via `scripts/checkout_sample.py`.

`docs/examples/` (static Dockerfile snippets, extension samples, JSON shapes) is unrelated and stays as documentation-only assets.

## Consequences

- One less tree to keep in sync with generator output.
- README and CONTRIBUTING point walkthrough commands at `tests/fixtures/…` instead of `examples/…`.
- Benchmark evidence, presentations, and `docker-smoke` CI use a pinned external sample checkout (see ADR 0009).

See also [`docs/POSITIONING.md`](../POSITIONING.md#sample-project-strategy-two-trees).

## Non-goals

- ~~Extracting the benchmark workload to a separate repository~~ — done in ADR 0009.
