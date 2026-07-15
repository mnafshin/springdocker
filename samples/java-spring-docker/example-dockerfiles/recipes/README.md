# Recipe presets

Reference Dockerfiles for each built-in `springdocker` recipe on the sample project's build tool.
Options come from the project's `.springdocker.toml` `[dockerfile]` section (runtime base, jlink, SBOM,
AppCDS, pinned digests, and so on); only the `recipe` field changes per file.

| File | Recipe | Purpose |
|---|---|---|
| `jvm-balanced.Dockerfile` | `jvm-balanced` | Default layered-JAR multi-stage JVM image |
| `spring-aot.Dockerfile` | `spring-aot` | Spring AOT processing in the build stage |
| `native-aot.Dockerfile` | `native-aot` | GraalVM native-image scaffold (experimental) |

## Runtime default (scenario 03 evidence)

Pinned sample results for jlink on each OS base (`benchmarks/03-base-image-choice/results/baseline.json`):

| Base | Image avg | Build avg | Startup avg |
|---|---:|---:|---:|
| alpine | 62.4 MB | 936 ms | 1,583 ms |
| **distroless** | **67.7 MB** | 959 ms | **1,511 ms** |
| debian-slim | 85.9 MB | **616 ms** | 1,584 ms |
| ubuntu | 85.9 MB | 984 ms | 1,673 ms |

`jvm-balanced` and `spring-aot` default to **distroless**: smaller than debian-slim (~21%) with faster startup,
at the cost of slower image builds. Pick alpine when every MB counts (verify musl). Pick debian-slim when build
speed matters most.

Regenerate with:

```bash
springdocker benchmark generate --project-root samples/java-spring-docker --java-version 25
```

Select a recipe when generating ad hoc output:

```bash
springdocker generate --project-root samples/java-spring-docker --recipe spring-aot
```

Source: https://github.com/mnafshin/springdocker
