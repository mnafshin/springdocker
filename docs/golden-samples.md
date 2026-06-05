# Golden sample projects

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

## Why these are canonical

- They are minimal enough to keep the CI matrix fast.
- They are representative of the two supported build-tool paths.
- They avoid duplicating sample apps in multiple directories.

