# Example generated Dockerfiles

Versioned reference output from `springdocker` for each benchmark scenario in this sample project.

Regenerate together with benchmark assets:

```bash
springdocker benchmark generate --project-root samples/java-spring-docker --java-version 25
```

Each `*.Dockerfile` under a scenario folder matches the corresponding variant under
`benchmarks/<scenario>/variants/` (those variant trees are gitignored and reproduced by the same command).

The `recipes/` folder shows the three built-in generation presets (`jvm-balanced`, `spring-aot`, `native-aot`)
for the configured build tool — use `springdocker generate --recipe <name>` to select one interactively.

Source: https://github.com/mnafshin/springdocker
