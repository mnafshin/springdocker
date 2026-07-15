# Compatibility matrix

> **Status: Implemented** — descriptive support ranges for the shipped CLI; not a formal certification matrix.

This repository documents the stack combinations that `springdocker` is designed to handle today.

| Component | Supported range | Notes |
|---|---|---|
| Python CLI | 3.10+ | Development and CI target. |
| Java | 17+ | Default fallback when undetected; Dockerfile generation rejects versions below 17. |
| JEP 483 AOT cache | 24+ | Explicit enable hard-fails below 24; benchmark scenario generated only for Java ≥ 24. |
| Spring Boot | 4.x sample project | The bundled sample project currently uses Spring Boot 4.0.1. |
| Docker | 24+ recommended | Multi-stage, BuildKit, and Buildx-friendly workflows are documented. |
| Architectures | amd64, arm64 | Multi-arch generation is Buildx-friendly when both platforms are available. |

## Policy notes

- CLI and init templates default to **Java 17** when the project version is undetected.
- The sample project is pinned to Java 25 for benchmark/presentation evidence (including the JEP 483 scenario).
- Multi-arch support is generated in the Dockerfile output, but the published matrix depends on the target platform and base image availability.
- The compatibility matrix is descriptive, not a promise that every combination has identical performance characteristics.
