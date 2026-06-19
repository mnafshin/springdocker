# ADR 0003: Dockerfile generation philosophy

## Status

Accepted (amended for [#108](https://github.com/mnafshin/springdocker/issues/108))

## Context

Dockerfile generation must preserve exact output expectations used by snapshots and explainability tests
while remaining easy to maintain.

Teams also need a clear, consistent story for **runtime readiness probing**:

- **Distroless** (the default `production-balanced` runtime) has no shell and no `wget`/`curl`.
- **OS-based runtimes** (debian-slim, alpine, ubuntu, temurin) can run a minimal in-image probe when
  Spring Boot Actuator is present.

Earlier wording in this ADR said the generator does not add Dockerfile healthchecks at all. That was
over-broad: OS runtime paths do emit an optional `HEALTHCHECK` instruction today.

## Decision

1. Use a structured in-memory representation for generation, but render the final text with exact line
   preservation.
2. Keep the generator opinionated about container-safe defaults (non-root, digest pins, jlink, layered JAR,
   supply-chain controls — see ADR 0005).
3. **Healthcheck policy is runtime-specific:**

   | Runtime base | Dockerfile `HEALTHCHECK` | Readiness probing |
   |---|---|---|
   | **distroless** (default) | **Omitted** — no shell, no `wget` in the image | Orchestrator layer (e.g. Kubernetes `readinessProbe` on `/actuator/health/readiness`) |
   | **debian-slim, alpine, ubuntu, temurin** | **Optional** — `wget`-based `HEALTHCHECK` when a health path is configured | Dockerfile probe when emitted; orchestrator probes still recommended in production |

4. **Auto-detect:** when `healthcheck_path` is unset (`__auto__`), the generator sets
   `/actuator/health/readiness` only if the project declares Spring Boot Actuator on the classpath.
5. **Do not** install `curl` (or other probe tooling) into generated images for healthchecks.
6. **Do not** emit Dockerfile `HEALTHCHECK` on distroless — even when actuator is detected. Distroless
   images cannot execute shell-form `CMD wget …` instructions.

Example OS-runtime instruction (when actuator is present):

```dockerfile
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD wget -qO- "http://localhost:8080/actuator/health/readiness" >/dev/null || exit 1
```

## Consequences

- Output stays stable enough for snapshot and explainability coverage.
- The Dockerfile generator remains deterministic and human-readable.
- **Distroless users** must configure readiness at the orchestrator layer — documented in
  [`cli/README.md`](../cli/README.md#runtime-bases-and-healthcheck) and presentation decks.
- **OS runtime users** get an actuator-aware Dockerfile probe when applicable; they can override or disable
  via `healthcheck_path` in `.springdocker.toml` or `--healthcheck-path` on the CLI.
- We avoid curl-in-Dockerfile patterns and avoid bloating minimal images with probe packages on distroless.

## References

- [#108 Update ADR 0003 healthcheck language](https://github.com/mnafshin/springdocker/issues/108)
- `src/springdocker/dockerfile.py` — `_os_runtime_section`, distroless runtime branch
- `src/springdocker/services/dockerfile_service.py` — `_resolve_healthcheck_path`
