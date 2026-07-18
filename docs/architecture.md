# Architecture

`springdocker` is organized around a small CLI core and a sample Spring Boot project that acts as the target for generation and benchmark workflows.

## High-level flow

```mermaid
flowchart TD
  user[User] --> cli[cli.py]
  cli --> config[config.py]
  cli --> commands[commands.py]
  commands --> services[services/*_service.py]
  commands --> detect[project_detect.py]
  commands --> dockerfile[dockerfile.py]
  commands --> explain[dockerfile_explain.py]
  commands --> analyze[analyze.py]
  commands --> benchgen[benchmarks/generate.py]
  commands --> benchr[benchmarks/runner.py]
  benchgen --> sample[java-spring-docker-sample checkout]
  benchr --> sample
```

## Module responsibilities

| Module | Responsibility |
|---|---|
| `src/springdocker/cli.py` | Parse CLI arguments and dispatch commands. |
| `src/springdocker/commands.py` | Thin command handlers for CLI output and exit-code mapping. |
| `src/springdocker/services/` | Command service layer for Dockerfile, benchmark, and project orchestration logic. |
| `src/springdocker/config.py` | Load `.springdocker.toml` and resolve command settings. |
| `src/springdocker/project_detect.py` | Detect Maven/Gradle markers, Spring Boot hints, and common multi-module layouts (Maven reactor / Gradle `include`). |
| `src/springdocker/dockerfile.py` | Render Dockerfiles from structured options. |
| `src/springdocker/dockerfile_explain.py` | Advisory Dockerfile explanation via static text heuristics (not a security audit; use `verify` for CI gates). |
| `src/springdocker/analyze.py` | Summarize benchmark CSV data and format reports. |
| `src/springdocker/benchmarks/` | Generate and run benchmark scenario assets. |

## CLI execution lifecycle

1. `cli.py` builds the parser.
2. `main()` resolves the project root and loads config when needed.
3. A resolver in `config.py` merges CLI flags, config files, and defaults.
4. `commands.py` delegates command logic to service-layer modules.
5. Service modules call supporting helpers to write files, render Dockerfiles, or analyze CSV output.

## Configuration resolution

The precedence used across the CLI is:

1. CLI flags
2. `.springdocker.toml`
3. built-in defaults

The configuration loader validates the schema early so invalid keys fail fast instead of being silently ignored.

## Dockerfile generation pipeline

`cmd_dockerfile_generate()`:

1. Inspects the project root and build tool.
2. Parses `must_have_modules_file` when provided.
3. Calls `build_dockerfile()` with structured options.
4. Writes the generated file to the target path.

`dockerfile.py` produces:

- multi-stage build stages
- optional jlink runtime stage
- non-root runtime defaults
- tuned JVM flags

## Benchmark pipeline

`cmd_benchmark_generate()` creates benchmark assets under the sample project.
`cmd_benchmark_run()` executes the benchmark runner and writes raw CSV output.
`cmd_benchmark_analyze()` reads CSV output and renders a summary table or JSON document.

This split keeps generation, execution, and reporting independent so each step can be validated on its own.

## Extension points

New features should usually be added in one of these places:

- CLI argument parsing: `cli.py`
- orchestration and validation: `commands.py`
- config schema and resolution: `config.py`
- Dockerfile output changes: `dockerfile.py`
- benchmark reporting: `analyze.py`
- third-party hooks: six entry-point groups in `plugins.py` — see [`adr/0001-plugin-architecture.md`](adr/0001-plugin-architecture.md) and [`extensions.md`](extensions.md)

If a change affects generated output, add tests for both the direct helper and the CLI flow that exercises it.
