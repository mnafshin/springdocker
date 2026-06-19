# ADR 0007: Jlink baseline modules scoped to Spring Web detection

## Status

Accepted (closes [#93](https://github.com/mnafshin/springdocker/issues/93))

## Context

When jlink is enabled, the generator merges **baseline modules** into the jlink `MUSTHAVE_MODULES`
list alongside jdeps output and curated modules from `must_have_modules_file`.

The default baseline (added in accabd3) is:

- `java.desktop` — JavaBeans / parts of the Spring Web stack
- `java.logging` — `java.util.logging` used by framework code
- `java.naming` — JNDI lookups jdeps often misses on servlet-style apps

Applying the full set to **every** jlink build is broader than necessary for non-web Spring Boot
workloads (batch, messaging-only, CLI) and can inflate custom runtimes without benefit.

## Decision

1. **Auto-inject the full baseline only when Spring Web markers are detected** in the project
   (directly or in a single detected Spring Boot submodule):
   - `spring-boot-starter-web`
   - `spring-boot-starter-webflux`
   - `spring-boot-starter-websocket`
2. **When Web is not detected**, auto baseline is **empty** — rely on jdeps plus
   `must_have_modules_file` for reflection/dynamic-loading edge cases.
3. **Explicit config always wins:** set `jlink_baseline_modules` in `.springdocker.toml` to override
   auto-detection, or `[]` to disable baseline injection entirely.
4. **Omit** `jlink_baseline_modules` from config (default init template) to use auto-detection at
   `dockerfile generate` time — same pattern as actuator-aware `healthcheck_path`.

Programmatic `DockerfileOptions` and benchmark asset generation may still pass an explicit baseline;
the config-driven CLI path resolves auto baseline from the project root.

## Consequences

- Non-web Spring Boot services get leaner jlink runtimes by default.
- Web/API services keep the defensive baseline without extra config.
- Teams with unusual stacks can pin modules explicitly in config or `must_have_modules_file`.
- `springdocker explain` continues to label baseline vs curated modules in output.

## References

- [#93 Scope default jlink modules to Spring Web detection](https://github.com/mnafshin/springdocker/issues/93)
- `src/springdocker/project_detect.py` — `has_spring_web_dependency`
- `src/springdocker/services/dockerfile_service.py` — `_resolve_jlink_baseline_modules`
