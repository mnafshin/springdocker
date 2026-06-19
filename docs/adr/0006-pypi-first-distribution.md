# ADR 0006: PyPI-first distribution

## Status

Accepted (closes [#97](https://github.com/mnafshin/springdocker/issues/97))

## Context

The repository ships two related surfaces:

| Surface | Role |
|---|---|
| **PyPI package `springdocker`** | Installable CLI for any Maven/Gradle Spring Boot project |
| **Git repository** | Source, CI, benchmark harness (`samples/java-spring-docker/`), presentations, contributor tooling |

Review question [#97](https://github.com/mnafshin/springdocker/issues/97) asked whether the primary path is PyPI (`pipx` / `uv tool`) or clone-and-run-benchmarks on the sample.

That choice affects README quick start, how much benchmark evidence belongs in the main tree, and whether docs imply every user must clone the repo.

## Decision

1. **Primary distribution is PyPI-first.** Users install `springdocker` and run it against **their own** Spring Boot project. Cloning the repository is not required for Dockerfile generation, explain, or verify workflows.
2. **Clone is secondary** — required only when the goal is:
   - reproducing or extending benchmark evidence under `samples/java-spring-docker/`
   - reading/updating presentation decks or pinned CI baselines
   - contributing to the CLI package
3. **Benchmarks remain in-repo** as optional evidence anchored to the sample app. They are not part of the default install story; use the `[benchmark]` extra when running `benchmark run` / analyze locally.
4. **README and onboarding** lead with `pipx` / `uv tool` / `pip install`, then document clone + editable install under development/contributing paths.

Recommended installs:

```bash
pipx install springdocker                  # Dockerfile workflow only
pipx install 'springdocker[benchmark]'     # + benchmark run/analyze (needs Docker)
```

## Consequences

- Quick start docs target an installed CLI on the user's project root, not `git clone` + `pip install -e .`.
- `samples/java-spring-docker/` stays the permanent benchmark harness (see ADR 0004); it is not deprecated in favor of PyPI-only distribution.
- `docs/distribution.md` describes PyPI as the shipped channel; Homebrew/Scoop/standalone binary remain roadmap.
- CI and contributor docs continue to use editable installs from a clone.

## References

- [#97 Distribution model](https://github.com/mnafshin/springdocker/issues/97)
- [ADR 0004: Sample project strategy](0004-sample-project-strategy.md)
- [`docs/POSITIONING.md`](../POSITIONING.md)
