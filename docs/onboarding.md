# Onboarding

This repository and CLI are named **springdocker** (`pip install springdocker`, command `springdocker`). The benchmark sample lives at `samples/java-spring-docker/` with Maven coordinates `io.github.mnafshin:java-spring-docker` — see [Project naming](../README.md#project-naming) in the README.

## 5-minute quickstart

1. Clone the repo.
2. Create and activate a virtual environment.
3. Install the package with `python3 -m pip install -e ".[dev]"`.
4. Run `springdocker doctor --project-root samples/java-spring-docker`.
5. Generate a Dockerfile with `springdocker dockerfile generate`.
6. Generate benchmark assets with `springdocker benchmark generate`.
7. Run the sample benchmark suite with `springdocker benchmark run --profile quick`.
8. Summarize one raw CSV file with `springdocker benchmark analyze`.

## Local development

- Use the sample project under `samples/java-spring-docker/` as the default target.
- Run the tests and linters before pushing.
- Keep docs and CLI flags in sync.

## What to look at first

- `README.md`
- `cli/README.md`
- `docs/architecture.md`
- `docs/benchmark-methodology.md`
- `docs/troubleshooting.md`

## Common workflows

| Goal | Command |
|---|---|
| Check the project | `springdocker doctor --project-root samples/java-spring-docker` |
| Write config | `springdocker init --project-root samples/java-spring-docker --build-tool maven` |
| Generate Dockerfile | `springdocker dockerfile generate --project-root samples/java-spring-docker` |
| Run benchmarks | `springdocker benchmark run --project-root samples/java-spring-docker --profile quick` |
