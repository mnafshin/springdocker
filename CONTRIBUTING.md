# Contributing

Thanks for helping improve `springdocker`.

## Project naming

The installable CLI, GitHub repository, and PyPI package are all **springdocker**. The benchmark sample lives in [`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample) and uses the Maven/Gradle artifact `io.github.mnafshin:java-spring-docker` for historical reasons — it is not the CLI package name. See the [naming table in README.md](README.md#project-naming).

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

Mypy runs on `src/` with gradual strictness — baseline settings plus per-module overrides for core modules. See [`docs/internal/typing.md`](docs/internal/typing.md) before tightening types or adding `# type: ignore`.

## Coverage policy

Local `pytest` and the CI `coverage` job enforce the same gate: **≥80% line coverage** on the entire
`springdocker` package (`pyproject.toml` → `[tool.pytest.ini_options]` → `addopts`). The README coverage badge links here.

- CI matrix jobs run one suite at a time (`unit`, `integration`, `e2e`, `benchmark`) with
  `--cov-fail-under=0` because partial runs cannot satisfy the global threshold.
- No modules are intentionally omitted from coverage measurement; every file under `src/springdocker/`
  counts toward the gate.
- Add or extend tests when your change touches untested paths — do not lower the threshold to land code.

## Reference sample checkout

Before docker-smoke or full benchmark workflows, check out the pinned sample:

```bash
python scripts/checkout_sample.py
# → samples/java-spring-docker/  (gitignored)
```

Pin: [`scripts/java_spring_docker_sample.manifest.json`](scripts/java_spring_docker_sample.manifest.json). Local tip: keep a sibling clone at `../java-spring-docker-sample`. See [`samples/README.md`](samples/README.md) and [ADR 0009](docs/adr/0009-external-sample-repository.md).

## Docker smoke build (CI)

The `docker-smoke` job runs `python scripts/docker_smoke_build.py` on Ubuntu with a real Docker daemon.
It checks out the pinned sample, generates a Dockerfile, builds the image, and probes actuator readiness
on port 8081. Integration/e2e tests keep mocking Docker for fast PR feedback; use the smoke script locally
when you change Dockerfile generation or runtime startup behavior:

```bash
python scripts/checkout_sample.py
python scripts/docker_smoke_build.py
```

## Consumer smoke — spring-petclinic (P3)

The `consumer-smoke-petclinic` workflow runs `python scripts/consumer_smoke_petclinic.py` against a **pinned**
[`spring-projects/spring-petclinic`](https://github.com/spring-projects/spring-petclinic) commit. It exercises
the documented onboarding path (`springdocker setup` → `verify --check-config-drift`) and then performs a real `docker build` plus actuator readiness on port 8080.

Pinned upstream revision: `scripts/consumer_smoke_petclinic.manifest.json`.

The smoke run selects the **`build-speed`** setup profile (debian-slim, no jlink) because jlink module
sets are application-specific; `production-balanced` + jlink is validated separately by the
`docker-smoke` job on the pinned [`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample) checkout.

**Local run** (requires Docker, git, and `springdocker` on `PATH`):

```bash
pip install -e .
export DOCKER_BUILDKIT=1
python scripts/consumer_smoke_petclinic.py
```

Do not pipe this script through `tee` without `set -o pipefail` — a failed `docker build` would otherwise report the pipe's exit code (0) instead of the script's.

PyPI-style install (no editable checkout):

```bash
pipx install springdocker
export DOCKER_BUILDKIT=1
python scripts/consumer_smoke_petclinic.py --springdocker-cmd springdocker
```

Useful flags while iterating:

```bash
# Onboarding + verify only (no docker build)
python scripts/consumer_smoke_petclinic.py --skip-docker-build

# Keep clone for inspection
python scripts/consumer_smoke_petclinic.py --keep-work-dir --work-dir .consumer-smoke-petclinic

# Re-run build against an existing clone
python scripts/consumer_smoke_petclinic.py --skip-clone --work-dir .consumer-smoke-petclinic
```

The job is scheduled weekly and on `main` changes to generator code; it is intentionally **not** part of the
fast PR matrix because Petclinic image builds can take 30–60+ minutes.

## Supply chain CI

The `supply-chain` job in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and pull request:

| Step | Behavior |
|---|---|
| SPDX SBOM | Uploaded as a workflow artifact (`sbom-spdx`) |
| Trivy filesystem scan | **Blocking** on unfixed **CRITICAL** vulnerabilities in the repository tree |

HIGH and lower severities do not fail that job. To gate Dockerfile build context on HIGH+CRITICAL locally or in your service pipeline, install `trivy` and run `springdocker verify` (see [`cli/README.md`](cli/README.md#verify-command) and [`docs/security.md`](docs/security.md)).

If a CRITICAL finding is a false positive or has no fix upstream, document the exception in `.trivyignore` and link the advisory in the pull request.

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
- `tests/fixtures/` for minimal CI/e2e walkthroughs ([POSITIONING](docs/POSITIONING.md#sample-project-strategy-two-trees))
- [`java-spring-docker-sample`](https://github.com/mnafshin/java-spring-docker-sample) (checkout via `scripts/checkout_sample.py`) for the full benchmark sample app and evidence assets

## Releases

- Release-please opens semantic version release PRs from `main`.
- The tag-publish workflow only runs after a `vX.Y.Z` tag exists.
- `CHANGELOG.md` is updated from the release process and published with each release.
- Repository setting required: **Settings → Actions → General → Workflow permissions** must be **Read and write**, with **Allow GitHub Actions to create and approve pull requests** enabled (otherwise release-please fails with “not permitted to create or approve pull requests”).
- Prefer [Conventional Commits](https://www.conventionalcommits.org/) on `main` (`feat:`, `fix:`, `docs:`, …) so release-please can infer version bumps and changelog entries.
