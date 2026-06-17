# Base image digest pin runbook

springdocker pins known-good base images by digest in [`src/springdocker/digest_pins.py`](../src/springdocker/digest_pins.py).
Generated Dockerfiles and snapshot tests inherit those pins through `dockerfile.py`.

## What is pinned today

| Pin label | Image | Registry |
|---|---|---|
| `temurin-jdk-{17,21,25}` | `eclipse-temurin:<version>-jdk` | Docker Hub |
| `temurin-jre-{17,21,25}` | `eclipse-temurin:<version>-jre` | Docker Hub |
| `distroless-java-{17,21}` | `gcr.io/distroless/java<version>-debian12:nonroot` | Google Container Registry |
| `distroless-base-debian12` | `gcr.io/distroless/base-debian12:nonroot` | Google Container Registry |
| `debian-bookworm-slim` | `debian:bookworm-slim` | Docker Hub |

OS runtime variants `ubuntu` and `alpine` intentionally use floating tags (no digest in catalog).

## Automation

| Mechanism | Scope |
|---|---|
| **Renovate** (`.github/renovate.json`) | Opens PRs when upstream images move; matches `ImagePin(...)` rows in `digest_pins.py` and digest-pinned `Dockerfile` snapshots. |
| **CI `digest-pins` job** | Runs `python scripts/verify_digest_pins.py` on every push — fails when a committed digest no longer resolves. |
| **Unit tests** | `tests/unit/test_digest_pins.py` validates catalog shape without network. |

Enable the Renovate GitHub App (or run Renovate in your org) for automated digest PRs. The config template is committed; it does not run by itself.

## Verify pins locally

```bash
python scripts/verify_digest_pins.py
```

Requires outbound HTTPS to `registry-1.docker.io`, `auth.docker.io`, and `gcr.io`.

## Rotate a digest manually

1. Pull or inspect the new image and copy its `sha256:` digest:

   ```bash
   docker pull eclipse-temurin:25-jdk
   docker inspect eclipse-temurin:25-jdk --format '{{index .RepoDigests 0}}'
   ```

2. Update the matching `ImagePin(...)` row in `src/springdocker/digest_pins.py`.
3. Run verification and tests:

   ```bash
   python scripts/verify_digest_pins.py
   pytest tests/unit/test_digest_pins.py tests/benchmark/test_dockerfile_snapshots.py -q
   ruff check src tests && mypy src
   ```

4. Commit `digest_pins.py` and any snapshot/dockerfile test updates in the same PR.

## When Renovate opens a digest PR

1. Confirm CI passes (`digest-pins`, snapshot tests, lint).
2. Skim the release notes/CVE context for the base image bump.
3. Merge — no separate runbook step unless generator output changed and snapshots need regeneration.

## Adding a new Java version pin

1. Add `temurin-jdk-*`, `temurin-jre-*`, and (if used) `distroless-java-*` rows to `IMAGE_PINS`.
2. Extend `.github/renovate.json` only if you introduce a new image naming pattern (existing regex covers `ImagePin` rows).
3. Run `verify_digest_pins.py` and update snapshot tests if default Java version changes.

See also [`security-hardening.md`](security-hardening.md) for runtime hardening and supply-chain context.
