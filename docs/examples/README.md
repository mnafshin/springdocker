# Examples

Committed reference artifacts for review (not a third “sample product”). Fixtures stay under `tests/fixtures/`; the benchmark sample is [`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample) — see [POSITIONING](../POSITIONING.md#sample-project-strategy-two-trees).

## Dockerfiles

| File | Shows |
|---|---|
| [baseline.Dockerfile](baseline.Dockerfile) | Minimal single-stage runtime |
| [jlink.Dockerfile](jlink.Dockerfile) | Multi-stage + custom jlink |
| [layered.Dockerfile](layered.Dockerfile) | Layered multi-stage without jlink |
| [distroless.Dockerfile](distroless.Dockerfile) | `jvm-balanced`-style distroless + jlink |

## Other

| Path | Shows |
|---|---|
| [benchmark-report.json](benchmark-report.json) | `benchmark analyze --format json` shape |
| [observability/](observability/) | Actuator/metrics + ServiceMonitor stubs |
| [distribution/](distribution/) | Roadmap install templates (Homebrew/Scoop/binary) — **PyPI is shipped** |
| [plugins/](plugins/) | Extension packaging examples |
