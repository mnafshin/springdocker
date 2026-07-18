# ADR 0005: Config-first Dockerfile generation

## Status

Accepted

## Context

`DockerfileOptions` models most generation decisions internally. Interactive generation is
provided by `springdocker configure`; deterministic CI generation uses `dockerfile generate`.

Teams need a reproducible, reviewable Dockerfile strategy in git. CI must generate Dockerfiles
without interactive prompts.

## Decision

1. **SSOT:** `.springdocker.toml` `[dockerfile]` is the single source of truth for generation
   decisions.
2. **Precedence:** CLI flags > project `.springdocker.toml` > built-in defaults. Org policy
   (`SPRINGDOCKER_POLICY`) is a follow-up layer documented in issue #123.
3. **Commands:**
   - `springdocker configure` — interactive wizard that writes/updates `[dockerfile]` in config.
   - `springdocker dockerfile generate` — non-interactive; reads resolved config only.
   - `springdocker init --interactive` — delegates to the same configure flow after creating
     the config skeleton.
4. **Profiles:** Named bundles (`production-balanced`, `smallest-image`, `fast-cold-start`,
   `build-speed`, `simplest`, `compliance`, `custom`) map to `DockerfileOptions` overlays.
   On save, profiles expand to explicit option keys for readable diffs.
5. **JVM flags:** `jvm_flags` is an explicit string list in config. When unset and
   `tuned_jvm_flags = true`, the generator applies the documented default bundle. When
   `jvm_flags` is set, it replaces the tuned bundle entirely.
6. **Digest pinning:** `pin_digests = true` (default) preserves current behavior. When
   `false`, image tags are emitted without `@sha256:` suffixes.
7. **Benchmark:** optional evidence workflow; never required before `dockerfile generate`.

## Consequences

- Teams commit `.springdocker.toml` and review Dockerfile strategy in PRs.
- CI runs `dockerfile generate` deterministically.
- The generator surface in config matches `DockerfileOptions` for explainability and testing.
- Legacy `tools/dockerfile_wizard.py` delegation is removed; use `configure` + `dockerfile generate`.
- The **Java builder plugin** is a separate surface with POM/Gradle SSOT — see [ADR 0010](0010-pom-gradle-ssot-java-builder.md). This ADR continues to govern the Python CLI / toml path only.

## References

- Epic #113
- ADR 0003 (Dockerfile generation philosophy)
- ADR 0010 (Java builder plugin; POM/Gradle SSOT)
- `docs/jvm.md`
