# Onboarding

**springdocker** is installed from PyPI (`pip install springdocker`, command `springdocker`). You do not need to clone this repository unless you are reproducing benchmarks, editing presentations, or contributing to the CLI.

See [Project naming](../README.md#project-naming) and [Install](../README.md#install) in the README.

## Consumer quickstart (PyPI)

Install on your machine, then run against your Spring Boot project:

```bash
pipx install springdocker
# or: pipx install 'springdocker[benchmark]' when you need benchmark run/analyze

cd /path/to/your-spring-boot-app
springdocker doctor --project-root .
springdocker init --project-root . --build-tool maven
springdocker configure --project-root . --force
springdocker dockerfile generate --project-root .
springdocker verify --project-root . Dockerfile.generated
```

Set `java_version` in `.springdocker.toml` to your service (**17+**). Undetected fallback is **17**. JEP 483 AOT requires **24+**.

Team rollout: [team-adoption.md](team-adoption.md).

## Contributor quickstart (clone)

1. Clone the repo.
2. Create and activate a virtual environment.
3. Install with `python3 -m pip install -e ".[dev]"`.
4. Run `pytest`, `ruff check src tests`, and `mypy src` before pushing.

Use `tests/fixtures/{maven-only,gradle-only}/` for CLI regression work. Use `samples/java-spring-docker/` for benchmark harness changes.

## Benchmark evidence (clone + Docker)

Requires repository clone, `[benchmark]` extra, and Docker. The sample pins **Java 25** so scenario 02 (JEP 483) is included:

```bash
pipx install 'springdocker[benchmark]'   # or editable .[dev] from a clone

springdocker benchmark generate --project-root samples/java-spring-docker --java-version 25
springdocker benchmark run --project-root samples/java-spring-docker --profile quick
springdocker benchmark analyze --project-root samples/java-spring-docker \
  samples/java-spring-docker/benchmarks/01-custom-jre-jlink/results/raw.csv --format table
```

On your own Java 17–23 service, scenario `02-jep483-aot-cache` is omitted; AppCDS (scenario 05) remains available.
## What to look at first

- `README.md` — install paths and when to clone
- `cli/README.md` — command reference
- `docs/POSITIONING.md` — PyPI vs sample tree
- `docs/team-adoption.md`
- `docs/architecture.md`
- `docs/benchmark-methodology.md`
- `docs/troubleshooting.md`

## Common workflows

| Goal | Command |
|---|---|
| Check the project | `springdocker doctor --project-root .` |
| Write config | `springdocker init --project-root . --build-tool maven` |
| Interactive Dockerfile strategy | `springdocker configure --project-root . --force` |
| Generate Dockerfile | `springdocker dockerfile generate --project-root .` |
| Run benchmarks (sample app) | `springdocker benchmark run --project-root samples/java-spring-docker --profile quick` |
