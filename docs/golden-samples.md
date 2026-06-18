# Golden sample projects

## Project map

| Path | Role |
|---|---|
| `tests/fixtures/{maven-only,gradle-only}/` | Minimal CLI walkthroughs and CI golden samples (this document) |
| `samples/java-spring-docker/` | Benchmark harness and versioned evidence |

Decision record for removing the former `examples/` walkthrough tree: [`adr/0004-sample-project-strategy.md`](adr/0004-sample-project-strategy.md).

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
| native JVM comparison scaffold | Scaffold only / roadmap | The `07-native-benchmark` scenario generates a `native-aot` Dockerfile scaffold; native-image execution remains out of scope. |

## Why fixtures are canonical for CI

- They are minimal enough to keep the CI matrix fast.
- They are representative of the two supported build-tool paths.
- They avoid duplicating sample apps in multiple directories.

The fixture projects below are also the README quick-start targets — copy or point `--project-root` at them when trying the CLI locally.

Real Docker build evidence uses the full sample app under `samples/java-spring-docker/` (see the `docker-smoke`
CI job and `scripts/docker_smoke_build.py`). The minimal fixtures above validate CLI output only — they do not
ship application source and are not used for container builds.

For how these paths relate to public guarantees vs benchmark evidence, see [`docs/POSITIONING.md`](../docs/POSITIONING.md).

