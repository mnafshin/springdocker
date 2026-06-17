# Benchmark methodology

This repository uses scenario-based Docker benchmarks against the sample Spring Boot project in `samples/java-spring-docker/`.
Benchmark commands are optional evidence workflows and require `springdocker[benchmark]`.

## Measurement model

Each benchmark run records one row per build-and-startup attempt with these fields:

- `date`
- `scenario`
- `variant`
- `run`
- `build_ms`
- `image_bytes`
- `startup_ms`
- `status`
- `notes`
- `host`
- `docker_version`
- `run_profile`

If available, the analyzer also reports RSS memory and CPU usage columns.

The runner writes rows into `results/raw.csv` next to each scenario.
Versioned reference evidence snapshots are published under `samples/java-spring-docker/benchmarks/reference/`.

## Repository artifact policy

Generated benchmark assets are **not committed** except where CI or docs explicitly need a pinned snapshot:

| Artifact | Committed? | Purpose |
|---|---|---|
| `benchmarks/*/variants/` | No | Regenerate with `springdocker benchmark generate`. |
| `benchmarks/*/results/raw.csv` | No (except scenario 06 sample file) | Local/CI run output. |
| `benchmarks/07-native-benchmark/Dockerfile` | No | Native scaffold; generator-owned. |
| `benchmarks/06-base-image-choice/results/baseline.json` | Yes | Regression gate in CI. |
| `benchmarks/reference/v1/` | Yes | Versioned evidence for comparisons and docs. |

After `benchmark generate`, `git status` under `samples/java-spring-docker/benchmarks/` should be clean.
CI enforces this in the `benchmark-hygiene` job.

See `samples/java-spring-docker/benchmarks/README.md` for the maintainer checklist.

## Run profiles

The CLI supports two profiles:

- `quick`
- `full`

Default run counts are scenario-aware:

- `04-jep483-aot-cache`: 8 runs for `quick`, 15 for `full`
- all other standard scenarios: 3 runs for `quick`, 10 for `full`

You can override the number of runs with `benchmark run --runner-arg --runs --runner-arg N`.

## What the runner measures

The internal runner captures:

1. Docker build time in milliseconds.
2. Image size from `docker image inspect`.
3. Startup time by probing `/actuator/health/readiness`.
4. Build or readiness failure status.
5. Host metadata and Docker version for traceability.

Warmup runs are optional and are executed before recording rows; they are excluded from `raw.csv`.

## Statistical handling

`springdocker benchmark analyze` summarizes the raw CSV with:

- mean build time
- build-time standard deviation
- build-time 95% confidence interval
- mean startup time
- startup standard deviation
- p95 startup time
- p99 startup time
- startup 95% confidence interval
- average image size
- average RSS memory
- average CPU usage
- success rate

When available, the analyzer also reports optional profiling columns for:

- GC pause duration
- allocation trend
- startup phase breakdown (`boot`, `context`, `web server`, and aggregate phase total)

Confidence intervals use a 95% normal-approximation interval (`mean ± 1.96 * stdev / sqrt(n)`) when at least two valid samples exist.

For historical regression tracking, save a baseline summary with `--output baseline.json` and compare later runs with `--baseline baseline.json --fail-on-regression-above 20`.

The CI workflow uses the checked-in sample baseline under `samples/java-spring-docker/benchmarks/06-base-image-choice/results/baseline.json` to fail fast when the sample report regresses beyond the configured threshold.

## Current sample comparison snapshot

For the current checked-in reference snapshot, the high-level decision matrix is:

| Scenario | Preferred strategy | Why |
|---|---|---|
| 01 Multi-stage structure | specialized multi-stage | lower image size and better build cost |
| 02 BuildKit cache | with-cache | much faster builds |
| 03 JLink + JDeps | with-jlink | smaller runtime image with similar startup |
| 04 JEP 483 AOT cache | with-aot-cache | better startup and tail latency |
| 05 JVM flags | workload-dependent | host sensitivity makes the winner variable |
| 06 Base image choice | workload-dependent | compare configured runtime bases (default: alpine, debian-slim, ubuntu, distroless, temurin) |
| 07 Native vs JVM | scaffold only | `native-aot` Dockerfile is generated for future comparison; the internal runner skips native scenarios |
| 08 AppCDS | with-appcds | faster startup from shared class archive |

Reference evidence files are versioned under:

- `samples/java-spring-docker/benchmarks/reference/v1/raw.csv`
- `samples/java-spring-docker/benchmarks/reference/v1/summary.json`

## Reproducibility controls

`springdocker benchmark run` supports optional isolation controls for more stable comparisons:

- `--cpuset-cpus` pins container execution to specific CPUs.
- `--memory` caps the container memory allocation.
- `--warmup-runs` performs discarded warmup probes before the measured runs.
- `--max-workers` runs standard scenarios concurrently with bounded worker parallelism.
- `--normalized-runtime` applies read-only/no-new-privileges/tmpfs runtime hardening.

The same keys can be set under `[benchmark.run]` in `.springdocker.toml`.

When a metric is missing, the analyzer leaves the field empty instead of failing the summary.

## Reproducibility notes

- Each scenario is stored in a stable directory name.
- Scenario variants are generated from the same `DockerfileOptions` inputs.
- The CSV schema is fixed and validated by the analyzer before aggregation.

### Configuring base-image variants (scenario 06)

Set runtime bases under `[benchmark.generate.base_image_choice]` in `.springdocker.toml`:

```toml
[benchmark.generate.base_image_choice]
variants = ["alpine", "debian-slim", "ubuntu", "distroless", "temurin"]
```

Aliases such as `debian-bookworm-slim`, `ubuntu-noble`, and `eclipse-temurin-jre` are accepted.
Slim OS images (`alpine`, `debian-slim`, `ubuntu`) bundle a jlink-built JVM; `temurin` and `distroless`
use pre-built Java runtime images for a closer “stock image” comparison.

## Current limitations

- The runner assumes Docker is available on the host.
- Native scenarios are scaffold-only: the internal runner skips them because native-image execution is not a shipped workflow yet (see `docs/native-image-roadmap.md`).
- The current reproducibility controls are opt-in and do not change defaults.
