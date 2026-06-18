# Recipe presets

Reference Dockerfiles for each built-in `springdocker` recipe on the sample project's build tool.

| File | Recipe | Purpose |
|---|---|---|
| `jvm-balanced.Dockerfile` | `jvm-balanced` | Default layered-JAR multi-stage JVM image |
| `spring-aot.Dockerfile` | `spring-aot` | Spring AOT processing in the build stage |
| `native-aot.Dockerfile` | `native-aot` | GraalVM native-image scaffold (experimental) |

Regenerate with:

```bash
springdocker benchmark generate --project-root samples/java-spring-docker --java-version 25
```

Select a recipe when generating ad hoc output:

```bash
springdocker generate --project-root samples/java-spring-docker --recipe spring-aot
```

Source: https://github.com/mnafshin/springdocker
