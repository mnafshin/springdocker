# ADR 0005: Config-first Dockerfile generation

## Status

Accepted

## Context

`DockerfileOptions` models most generation decisions internally, but only a subset is exposed
via `.springdocker.toml` and CLI. Interactive generation is split between the internal generator
and legacy `tools/dockerfile_wizard.py`.

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
8. **Legacy wizard:** `--use-legacy-scripts` and `wizard_args` are deprecated in favor of
   `configure` + `dockerfile generate`.

## Consequences

- Teams commit `.springdocker.toml` and review Dockerfile strategy in PRs.
- CI runs `dockerfile generate` deterministically.
- The generator surface in config matches `DockerfileOptions` for explainability and testing.
- Legacy script delegation can be removed after one release cycle with deprecation warnings.

## References

- Epic #113
- ADR 0003 (Dockerfile generation philosophy)
- `docs/jvm-optimization.md`
