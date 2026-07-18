# JVM / Java feature matrix

`springdocker` supports a small, explicit set of JVM/runtime choices in generated Dockerfiles.

## Support ranges

| Component | Range | Notes |
|---|---|---|
| Java | **17+** | Undetected / init fallback **17**; rejects below 17 |
| JEP 483 AOT cache | **24+** | Hard-fails below 24; benchmark scenario 02 only when ≥ 24 |
| Python CLI | 3.10+ | CI tests 3.10–3.12 |
| Architectures | amd64, arm64 | Buildx-friendly `TARGETPLATFORM` / `BUILDPLATFORM` |
| Sample evidence | Java **25** | [`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample) — not a CLI requirement |

## Current defaults

- non-root runtime user
- `-XX:MaxRAMPercentage=75`
- `-XX:+ExitOnOutOfMemoryError`
- `-Djava.io.tmpdir=/tmp`
- optional jlink runtime stage

Configure via `[dockerfile].jvm_flags` or `tuned_jvm_flags = true`. Set `pin_digests = false` to emit unpinned tags.

## Why these choices exist

- `MaxRAMPercentage` keeps container memory proportional to the cgroup limit
- `ExitOnOutOfMemoryError` fails fast
- `java.io.tmpdir=/tmp` keeps temp writes in the container filesystem
- jlink reduces runtime surface when a custom runtime is appropriate

## Tradeoffs

| Strategy | Benefit | Cost |
|---|---|---|
| Plain JRE | simplest | larger image |
| jlink | smaller / controlled | extra build step |
| tuned JVM flags | better container defaults | less portable across workloads |

## Feature scope

| Feature | Min Java | Notes |
|---|---|---|
| jlink, layered JAR, AppCDS, tuned JVM flags | 17 | Always available on supported JDKs |
| JEP 483 AOT cache | 24 | Explicit enable hard-fails below 24 |
| Profile `fast-cold-start` | 17 | AOT on 24+; remaps to AppCDS on 17–23 |

`enable_appcds` and `enable_jep483_aot_cache` are mutually exclusive.

Benchmark scenarios: `02-jep483-aot-cache` (Java ≥ 24 only), `05-appcds` (Java 17+) — see [benchmarks.md](benchmarks.md).
