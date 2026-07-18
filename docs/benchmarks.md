# Benchmark methodology

This repository uses scenario-based Docker benchmarks against the pinned
[`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample)
checkout (`python scripts/checkout_sample.py` → `samples/java-spring-docker/`).
Benchmark commands are optional evidence workflows and require `springdocker[benchmark]`.

## Scenario index

Authoritative list under the sample’s `benchmarks/` directory. Regenerate with `springdocker benchmark generate`. Scenario **04** (native) is listed before **05** (AppCDS) by id; the generator emits AppCDS before the native scaffold.

| ID | Directory | Purpose | Variants | Further reading |
|---|---|---|---|---|
| 01 | `01-custom-jre-jlink` | jlink vs vendor JRE vs Temurin image | `with-jlink-runtime`, `without-jlink-runtime`, `temurin-jre-image` | [jvm.md](jvm.md) |
| 02 | `02-jep483-aot-cache` | JEP 483 AOT (Java 24+; **generated only when ≥ 24**) | `with-aot-cache`, `without-aot-cache` | [jvm.md](jvm.md) · 8 quick / 15 full runs |
| 03 | `03-base-image-choice` | OS base tradeoffs (jlink on every base) | configurable | [base-image variants](#configuring-base-image-variants-scenario-03) · CI baseline |
| 04 | `04-native-benchmark` | Native scaffold (`native-aot`); skipped by default | single Dockerfile at scenario root | [native-aot.md](native-aot.md) |
| 05 | `05-appcds` | AppCDS shared archive | `with-appcds`, `without-appcds` | [jvm.md](jvm.md) |

```bash
springdocker benchmark analyze --project-root samples/java-spring-docker \
  benchmarks/01-custom-jre-jlink/results/raw.csv --format table
```

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
The CI regression gate uses a pinned sample pair under `benchmarks/03-base-image-choice/results/`.

## Repository artifact policy

Generated benchmark assets are **not committed** except where CI or docs explicitly need a pinned snapshot:

| Artifact | Committed? | Purpose |
|---|---|---|
| `benchmarks/*/variants/` | No | Regenerate with `springdocker benchmark generate`. |
| `benchmarks/*/results/raw.csv` | No (except scenario 03 sample file) | Local/CI run output. |
| `benchmarks/04-native-benchmark/Dockerfile` | No | Native scaffold; generator-owned. |
| `benchmarks/03-base-image-choice/results/raw.csv` | Yes | Pinned sample runs fed to the CI regression gate. |
| `benchmarks/03-base-image-choice/results/baseline.json` | Yes | Expected `benchmark analyze` output for that CSV. |
| `benchmarks/03-base-image-choice/results/baseline.manifest.json` | Yes | Documents how the baseline pair is regenerated. |

After `benchmark generate`, `git status` under the sample checkout’s `benchmarks/` should be clean.
CI enforces this in the `benchmark-hygiene` job (against the pinned sample repo).

CI does **not** run full Docker benchmark builds on every push — the regression gate validates analyzer output against a pinned baseline only. See [`POSITIONING.md`](POSITIONING.md#shipped-guarantees-ci-evidenced).

See the sample’s [`benchmarks/README.md`](https://github.com/mnafshin/java-spring-docker-sample/blob/main/benchmarks/README.md) for the maintainer checklist.

## CI regression baseline (scenario 03)

**Decision:** the regression gate uses **committed, paired artifacts** — not a baseline generated fresh in CI on every push.

| File | Role |
|---|---|
| `03-base-image-choice/results/raw.csv` | Pinned sample benchmark rows (input). |
| `03-base-image-choice/results/baseline.json` | Expected `springdocker benchmark analyze` summary for that CSV (source of truth). |
| `03-base-image-choice/results/baseline.manifest.json` | Regeneration command and provenance metadata. |

### What CI does

The `benchmark-regression` job in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml):

1. Runs `benchmark analyze` on the committed `raw.csv`.
2. Fails if the JSON summary is not **byte-identical** to committed `baseline.json` (catches drift when only one file is updated).
3. Runs the regression comparator with `--fail-on-regression-above 20` (catches analyzer changes that shift metrics without a baseline refresh).

CI does **not** execute Docker builds for this gate. The pinned CSV is sample evidence from a prior local `benchmark run`.

### How to refresh the baseline

After an intentional benchmark run or analyzer change (in the sample checkout or clone):

```bash
python scripts/checkout_sample.py   # from springdocker root, if needed

# 1. Update raw.csv (typically from a local benchmark run)
springdocker benchmark run --project-root samples/java-spring-docker --profile quick

# 2. Regenerate baseline.json from the CSV
springdocker benchmark analyze \
  --project-root samples/java-spring-docker \
  benchmarks/03-base-image-choice/results/raw.csv \
  --format json \
  --output benchmarks/03-base-image-choice/results/baseline.json

# 3. Commit both files in java-spring-docker-sample, then bump the pin here
cd samples/java-spring-docker   # or the sample clone
git add benchmarks/03-base-image-choice/results/raw.csv \
        benchmarks/03-base-image-choice/results/baseline.json
# after push: update scripts/java_spring_docker_sample.manifest.json ref in springdocker
```

Do not commit `baseline.json` without the matching `raw.csv`. Other scenarios keep `results/` gitignored; scenario 03 is the sole CI regression anchor today.

Analyzer summaries round derived metrics to six decimal places so `baseline.json` stays byte-stable across Python 3.10+ (the stdlib `statistics.quantiles` implementation differs slightly before 3.11).

## Run profiles

The CLI supports two profiles:

- `quick`
- `full`

Default run counts are scenario-aware:

- `02-jep483-aot-cache`: 8 runs for `quick`, 15 for `full` — **generated and run only when `java_version >= 24`**
- all other standard scenarios: 3 runs for `quick`, 10 for `full` (including `05-appcds` on Java 17+)

The reference sample pins Java 25 so the full scenario set (including JEP 483) is present for presentations and local full runs. On a Java 17–23 service, regenerate and runner omit scenario 02.

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

The repository pins one such pair for CI — see [CI regression baseline (scenario 03)](#ci-regression-baseline-scenario-03).

## Current sample comparison snapshot

For decision guidance per scenario, see the [scenario index](#scenario-index).

For the current checked-in reference snapshot, the high-level decision matrix is:

| Scenario | Preferred strategy | Why |
|---|---|---|
| 01 JLink + JDeps | with-jlink | ~20% smaller image on same debian-slim base; startup within noise |
| 02 JEP 483 AOT cache | with-aot-cache | better startup and tail latency |
| 03 Base image choice | distroless + jlink | `jvm-balanced` generator default; scenario 03 benchmarks alpine, debian-slim, ubuntu, and distroless when tuning |
| 04 Native vs JVM | scaffold only | `native-aot` Dockerfile is generated for future comparison; the internal runner skips native scenarios |
| 05 AppCDS | with-appcds | faster startup from shared class archive |

Pinned CI regression evidence (scenario 03 base-image choice) lives in
[`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample):

- `benchmarks/03-base-image-choice/results/raw.csv`
- `benchmarks/03-base-image-choice/results/baseline.json`

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

### Configuring base-image variants (scenario 03)

Set runtime bases under `[benchmark.generate.base_image_choice]` in `.springdocker.toml`:

```toml
[benchmark.generate.base_image_choice]
variants = ["alpine", "debian-slim", "ubuntu", "distroless"]
```

Aliases such as `debian-bookworm-slim`, `ubuntu-noble`, and `eclipse-temurin-jre` are accepted.
Slim OS images (`alpine`, `debian-slim`, `ubuntu`) default to a jlink-built JVM when `use_jlink=True`.
When `use_jlink=False` on those bases, springdocker copies a pinned vendor Temurin JRE into the OS
runtime stage (scenario 01 `without-jlink-runtime`). Scenario 01 `temurin-jre-image` uses the stock
`eclipse-temurin` JRE container image as shipped. Scenario 03 enables jlink for every configured base
(`distroless/base` + copied jlink runtime).

## Current limitations

- The runner assumes Docker is available on the host.
- Native scenarios are scaffold-only: the internal runner skips them (see [native-aot.md](native-aot.md)).
- The current reproducibility controls are opt-in and do not change defaults.
