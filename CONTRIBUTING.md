# Contributing

Thanks for helping improve `springdocker`.

## Local setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

## Before you push

Run the existing checks:

```bash
pytest
ruff check src tests
mypy src
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
- `examples/spring-boot-maven/` and `examples/spring-boot-gradle/` for human walkthroughs (README quick start)
- `tests/fixtures/` for minimal CI/e2e golden samples ([`docs/golden-samples.md`](docs/golden-samples.md))
- `samples/java-spring-docker/` for the full benchmark sample app and evidence assets

## Releases

- Release-please opens semantic version release PRs from `main`.
- The tag-publish workflow only runs after a `vX.Y.Z` tag exists.
- `CHANGELOG.md` is updated from the release process and published with each release.
