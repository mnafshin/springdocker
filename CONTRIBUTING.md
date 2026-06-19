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

Ruff runs with **F**, **I**, **B** (bugbear), **UP** (pyupgrade), and **SIM** (simplify) — see `[tool.ruff.lint]` in `pyproject.toml`. Fix auto-fixable issues with `ruff check src tests --fix`.

Mypy runs on `src/` with gradual strictness — baseline settings plus per-module overrides for core modules. See [`docs/typing-roadmap.md`](docs/typing-roadmap.md) before tightening types or adding `# type: ignore`.

## Coverage policy

Local `pytest` and the CI `coverage` job enforce the same gate: **≥80% line coverage** on the entire
`springdocker` package (`pyproject.toml` → `[tool.pytest.ini_options]` → `addopts`).

- CI matrix jobs run one suite at a time (`unit`, `integration`, `e2e`, `benchmark`) with
  `--cov-fail-under=0` because partial runs cannot satisfy the global threshold.
- No modules are intentionally omitted from coverage measurement; every file under `src/springdocker/`
  counts toward the gate.
- Add or extend tests when your change touches untested paths — do not lower the threshold to land code.

## Docker smoke build (CI)

The `docker-smoke` job runs `python scripts/docker_smoke_build.py` on Ubuntu with a real Docker daemon.
It generates a Dockerfile for `samples/java-spring-docker`, builds the image, and probes actuator readiness
on port 8081. Integration/e2e tests keep mocking Docker for fast PR feedback; use the smoke script locally
when you change Dockerfile generation or runtime startup behavior:

```bash
python scripts/docker_smoke_build.py
```

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
- `tests/fixtures/maven-only/` and `tests/fixtures/gradle-only/` for README quick-start Dockerfile workflows
- `tests/fixtures/` for minimal CI/e2e golden samples ([`docs/golden-samples.md`](docs/golden-samples.md))
- `samples/java-spring-docker/` for the full benchmark sample app and evidence assets

## Releases

- Release-please opens semantic version release PRs from `main`.
- The tag-publish workflow only runs after a `vX.Y.Z` tag exists.
- `CHANGELOG.md` is updated from the release process and published with each release.
- Repository setting required: **Settings → Actions → General → Workflow permissions** must be **Read and write**, with **Allow GitHub Actions to create and approve pull requests** enabled (otherwise release-please fails with “not permitted to create or approve pull requests”).
- Prefer [Conventional Commits](https://www.conventionalcommits.org/) on `main` (`feat:`, `fix:`, `docs:`, …) so release-please can infer version bumps and changelog entries.
