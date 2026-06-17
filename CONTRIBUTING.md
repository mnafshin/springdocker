# Contributing

Thanks for helping improve `springdocker`.

## Project naming

The installable CLI, GitHub repository, and PyPI package are all **springdocker**. The benchmark sample under `samples/java-spring-docker/` uses the Maven/Gradle artifact `io.github.mnafshin:java-spring-docker` for historical reasons — it is not the CLI package name. See the [naming table in README.md](README.md#project-naming).

## Local setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

## IntelliJ / PyCharm

See [`docs/ide/intellij.md`](docs/ide/intellij.md) if the IDE reports many errors in `dockerfile.py` while `mypy` passes (usually Dockerfile language injection or missing `src` sources root).

## Before you push

Run the existing checks:

```bash
pytest
ruff check src tests
mypy src
```

## Coverage policy

Local `pytest` and the CI `coverage` job enforce the same gate: **≥80% line coverage** on the entire
`springdocker` package (`pyproject.toml` → `[tool.pytest.ini_options]` → `addopts`).

- CI matrix jobs run one suite at a time (`unit`, `integration`, `e2e`, `benchmark`) with
  `--cov-fail-under=0` because partial runs cannot satisfy the global threshold.
- No modules are intentionally omitted from coverage measurement; every file under `src/springdocker/`
  counts toward the gate.
- Add or extend tests when your change touches untested paths — do not lower the threshold to land code.

## Change shape

- Keep commits small and focused.
- Add or update tests when behavior changes.
- Update docs when you change CLI flags, generated output, or benchmark flow.
- Add an ADR under `docs/adr/` when a change alters the plugin model, benchmark methodology,
  Dockerfile-generation philosophy, or another cross-cutting project decision.

## Code layout

- `src/springdocker/` for CLI and core logic
- `tests/unit/` for pure unit coverage
- `tests/integration/` for command and flow coverage
- `tests/e2e/` for end-to-end CLI flows
- `tests/benchmark/` for benchmark and snapshot coverage
- `examples/spring-boot-maven/` and `examples/spring-boot-gradle/` for human walkthroughs (README quick start)
- `tests/fixtures/` for minimal CI/e2e golden samples ([`docs/golden-samples.md`](docs/golden-samples.md))
- `samples/java-spring-docker/` for the full benchmark sample app and evidence assets

## Releases

- Release-please opens semantic version release PRs from `main`.
- The tag-publish workflow only runs after a `vX.Y.Z` tag exists.
- `CHANGELOG.md` is updated from the release process and published with each release.
