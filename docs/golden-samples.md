# Golden sample projects

## Project map

| Path | Role |
|---|---|
| `examples/spring-boot-{maven,gradle}/` | Human walkthroughs — see [`examples/README.md`](../examples/README.md) |
| `tests/fixtures/{maven-only,gradle-only}/` | CI golden samples (this document) |
| `samples/java-spring-docker/` | Benchmark harness and versioned evidence |

The repository keeps two canonical golden sample project paths for end-to-end CLI coverage:

| Sample | Path | Coverage status | Notes |
|---|---|---|---|
| Maven-only | `tests/fixtures/maven-only` | Covered end-to-end | Exercises Maven detection, Dockerfile generation, and benchmark asset generation. |
| Gradle-only | `tests/fixtures/gradle-only` | Covered end-to-end | Exercises Gradle detection, Dockerfile generation, and benchmark asset generation. |

## Variant coverage

The same E2E paths validate generated variant families that the benchmark generator owns:

| Variant family | Status | Notes |
|---|---|---|
| jlink runtime | Covered via generated benchmark asset | Verified through the `03-custom-jre-jlink` scenario. |
| distroless runtime | Covered via generated benchmark asset | Verified through the `06-base-image-choice` scenario. |
| native JVM comparison scaffold | Placeholder / roadmap | The `07-native-benchmark` scenario is generated, but native-image execution remains out of scope. |

## Why fixtures are canonical for CI

- They are minimal enough to keep the CI matrix fast.
- They are representative of the two supported build-tool paths.
- They avoid duplicating sample apps in multiple directories.

The `examples/` walkthrough projects are additionally covered by e2e tests so README quick-start paths cannot drift from the CLI.

