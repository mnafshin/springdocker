# Example projects

This directory contains isolated sample projects by build tool:

- `spring-boot-maven/`
- `spring-boot-gradle/`

These are the **preferred entry point** for human walkthroughs: copy the layout, run `springdocker init`, and generate a Dockerfile without pulling in the full benchmark sample.

## When to use which project path

| Path | Role |
|---|---|
| `examples/spring-boot-{maven,gradle}/` | Quick-start walkthroughs (this directory) |
| `tests/fixtures/{maven-only,gradle-only}/` | Minimal projects used by CI and e2e tests |
| `samples/java-spring-docker/` | Full Spring Boot app with benchmark scenarios and reference data |

See [`docs/golden-samples.md`](../docs/golden-samples.md) for how fixtures and benchmark variants are covered in tests.

The benchmark sample under `samples/java-spring-docker/` is intentionally heavier and is not required for basic Dockerfile workflows.
