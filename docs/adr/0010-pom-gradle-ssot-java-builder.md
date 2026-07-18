# ADR 0010: POM/Gradle SSOT for the Java builder plugin

## Status

Accepted (closes [#140](https://github.com/mnafshin/springdocker/issues/140))

Milestone: [Java builder plugin (POM/Gradle SSOT)](https://github.com/mnafshin/springdocker/milestone/3)

## Context

Production Spring Boot teams often prefer configuring builds in `pom.xml` / `build.gradle` rather than installing a Python CLI or maintaining `.springdocker.toml`. Reviewers asked for a **Maven/Gradle builder** that does not require Python at runtime.

Options considered:

1. **Maven plugin that shells out to the Python CLI** — familiar Mojo UX, but still needs `springdocker` / `uv` / `pipx` on the agent.
2. **Pure-Java builder plugin** with **POM/Gradle as SSOT** — JDK + Maven/Gradle only; optional bridge to the CLI later.
3. **Runtime library on the app classpath** — wrong fit; Dockerfile generation is a build concern.

[ADR 0005](0005-config-first-dockerfile-generation.md) remains correct for the **Python CLI** surface (`.springdocker.toml` SSOT). This ADR defines a **second surface** for Java build tools.

A transitional **CLI-wrapper** Maven plugin (Mojo → `springdocker` subprocess) was prototyped during exploration and kept only in a local git stash. It is **not** shipped on this branch and **must not** be published. The supported Java UX is the **pure-Java** builder under `integrations/maven-plugin` (and the Gradle twin). Anyone who installed an experimental `1.2.0-SNAPSHOT` wrapper locally should remove it from `~/.m2` and switch to the pure-Java plugin coordinates on this branch ([#148](https://github.com/mnafshin/springdocker/issues/148)).

## Decision

### Two surfaces

| Surface | SSOT | Audience | Scope |
|---|---|---|---|
| **Python CLI** (`springdocker`) | `.springdocker.toml` | Full toolkit users | setup, profiles, explain, verify, benchmarks, CI helpers |
| **Java builder plugin** (Maven now; Gradle follow-up) | `pom.xml` / `build.gradle` plugin configuration | Teams that only need a Dockerfile from the build | generate (+ verify); no benchmarks |

### Plugin SSOT rules

1. **POM / Gradle configuration is the single source of truth** for the builder plugin.
2. The plugin **must not require** `.springdocker.toml` for `generate` / `verify`.
3. The plugin **must not read** `.springdocker.toml` as input for generation decisions.
4. **Optional one-way export** of `.springdocker.toml` from plugin config is allowed so teams can later adopt the Python CLI ([#143](https://github.com/mnafshin/springdocker/issues/143)). Never the reverse as plugin SSOT.
5. **Benchmarks stay CLI-only.** Advanced tooling is out of the plugin.

### Relationship to ADR 0005

- ADR 0005 continues to govern the CLI / toml path.
- This ADR governs the Java builder path only.
- Docs must present both surfaces without implying every Java team must use Python ([#147](https://github.com/mnafshin/springdocker/issues/147)).

## Consequences

- Implement a pure-Java `generate` Mojo ([#142](https://github.com/mnafshin/springdocker/issues/142)) with a documented pom option subset ([#141](https://github.com/mnafshin/springdocker/issues/141)).
- Plugin verify checks drift against **plugin config**, not toml ([#144](https://github.com/mnafshin/springdocker/issues/144)).
- Publish to Maven Central for easy adoption ([#145](https://github.com/mnafshin/springdocker/issues/145)); Gradle twin later ([#146](https://github.com/mnafshin/springdocker/issues/146)).
- Dual front-ends to similar generation logic are accepted if the plugin stays a **thin, opinionated subset** of CLI capabilities.

## References

- Milestone: https://github.com/mnafshin/springdocker/milestone/3
- [#140](https://github.com/mnafshin/springdocker/issues/140) ADR acceptance
- [ADR 0005: Config-first Dockerfile generation](0005-config-first-dockerfile-generation.md) (CLI / toml)
- [ADR 0006: PyPI-first distribution](0006-pypi-first-distribution.md) (CLI distribution)
