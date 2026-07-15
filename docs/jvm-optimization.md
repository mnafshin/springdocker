# JVM optimization strategies

`springdocker` currently supports a small, explicit set of JVM/runtime choices in generated Dockerfiles.

## Current defaults

- non-root runtime user
- `-XX:MaxRAMPercentage=75`
- `-XX:+ExitOnOutOfMemoryError`
- `-Djava.io.tmpdir=/tmp`
- optional jlink runtime stage

Configure explicitly via `[dockerfile].jvm_flags` in `.springdocker.toml`, or use `tuned_jvm_flags = true` to apply the default bundle. Set `pin_digests = false` to emit unpinned image tags.

## Why these choices exist

- `MaxRAMPercentage` keeps container memory use proportional to the cgroup limit.
- `ExitOnOutOfMemoryError` fails fast instead of leaving a stuck JVM.
- `java.io.tmpdir=/tmp` keeps temporary writes inside the container filesystem.
- jlink reduces the runtime surface area when a custom runtime is appropriate.

## Tradeoffs

| Strategy | Benefit | Cost |
|---|---|---|
| Plain JRE | simplest runtime | larger image |
| jlink runtime | smaller and more controlled runtime | extra build step |
| tuned JVM flags | better container defaults | less JVM portability across workloads |

## Current scope

Floor is **Java 17**. Feature availability:

| Feature | Min Java | Notes |
|---|---|---|
| jlink, layered JAR, AppCDS, tuned JVM flags | 17 | Always available on supported JDKs |
| JEP 483 AOT cache | 24 | Explicit `enable_jep483_aot_cache` hard-fails below 24 |
| Profile `fast-cold-start` | 17 | Uses AOT on 24+; remaps to AppCDS on 17–23 |

`DockerfileOptions` exposes `enable_appcds` (AppCDS archive training) and `enable_jep483_aot_cache`
(JEP 483 ahead-of-time class-loading cache). The two options are mutually exclusive.

Benchmark scenarios isolate each optimization:

- `02-jep483-aot-cache`: toggles JEP 483 AOT cache only (generated only when project Java ≥ 24)
- `05-appcds`: toggles AppCDS only (Java 17+)

GC tuning is not yet a first-class option. The benchmark analyzer can still surface optional
GC/allocation/startup-phase profiling columns when they are present in `raw.csv`.
