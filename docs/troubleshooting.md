# Troubleshooting

## `springdocker doctor` reports project detection failures

- Confirm `--project-root` points at a Spring Boot project.
- Ensure `pom.xml`, `build.gradle`, or `build.gradle.kts` exists in the project root.
- Run `springdocker inspect --project-root <path> --format json` to see detected metadata.
- For Maven reactors or Gradle multi-project repos, inspect `layout` and `spring_boot_modules` in the JSON output — you may need `--project-root path/to/service-module`. See [`project-detection.md`](project-detection.md).

## Multi-module / monorepo layouts

- Root aggregator POMs often lack Spring Boot dependencies; run generation from the bootable submodule.
- `springdocker inspect` recommends `--project-root` when it finds a single Spring Boot module under a reactor.
- Exotic layouts (dynamic Gradle includes, Bazel, mixed tooling) need a `springdocker.project_detectors` plugin — examples in [`docs/examples/extensions/`](examples/extensions/).

## `springdocker dockerfile generate` fails

- Run `springdocker init --project-root <path>` first to create `.springdocker.toml`.
- Ensure the configured Java version is 17 or newer.
- Re-run with `--print` to inspect generated output before writing files.

## Benchmark commands fail

- Verify Docker is available locally (`docker --version`).
- Check out the reference sample (`python scripts/checkout_sample.py`) when reproducing examples that use `samples/java-spring-docker/`.
- Start with quick profile:
  `springdocker benchmark run --project-root samples/java-spring-docker --profile quick`

## CI behavior differs from local

- Use a clean virtual environment:
  `python3 -m venv .venv && . .venv/bin/activate`
- Install development dependencies:
  `python -m pip install -e ".[dev]"`
- Run the same checks as CI:
  `ruff check src tests && mypy && pytest -q`
