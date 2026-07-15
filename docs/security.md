# Security

Generated Dockerfiles favor safer defaults: non-root user, writable `/tmp`, distroless support, container-friendly JVM flags, and optional digest-pinned bases.

## Runtime recommendations

```bash
docker run --read-only --cap-drop=ALL --security-opt=no-new-privileges --tmpfs /tmp app:latest
```

- `--read-only` limits accidental writes
- `--cap-drop=ALL` reduces capability exposure
- `--security-opt=no-new-privileges` blocks privilege escalation
- `--tmpfs /tmp` keeps the JVM temp directory writable

## Supply-chain hygiene

- Pin base images by digest (`pin_digests = true`) — see [Digest pins](#digest-pins) below
- Ship an SBOM (`include_embedded_sbom`)
- Sign images before release; scan regularly

### Repository CI vs `springdocker verify`

| Surface | Scope | Severities | Blocks |
|---|---|---|---|
| GitHub Actions `supply-chain` | Full checkout | CRITICAL only | Yes |
| `springdocker verify` | Dockerfile context (or `--trivy-scan-project-root`) | HIGH+CRITICAL | When you run verify with `trivy` installed |

CI also publishes an SPDX SBOM artifact; releases sign with Cosign.

## Digest pins

Pins live in [`src/springdocker/digest_pins.py`](../src/springdocker/digest_pins.py).

| Pin label | Image |
|---|---|
| `temurin-jdk-{17,21,25}` / `temurin-jre-*` | Eclipse Temurin |
| `distroless-java-{17,21}` | `gcr.io/distroless/java*-debian12:nonroot` |
| `distroless-base-debian12` / `debian13` | jlink/native runtime (debian13 for Java 25+) |
| `debian-bookworm-slim`, `ubuntu-noble`, `alpine-3-21` | OS bases |

### Automation

| Mechanism | Role |
|---|---|
| Renovate (`.github/renovate.json`) | PRs when upstream digests move |
| CI `digest-pins` job | `python scripts/verify_digest_pins.py` |
| Unit tests | Catalog shape without network |

```bash
python scripts/verify_digest_pins.py
```

### Rotate a digest

1. `docker pull …` and copy `sha256` from `docker inspect … --format '{{index .RepoDigests 0}}'`
2. Update the `ImagePin(...)` row in `digest_pins.py`
3. `python scripts/verify_digest_pins.py` then `pytest tests/unit/test_digest_pins.py tests/benchmark/test_dockerfile_snapshots.py -q`
4. Commit pins + snapshots together

When Renovate opens a digest PR: confirm CI, skim CVE context, merge.

### New Java version pin

Add matching Temurin (and distroless-java if used) rows; extend Renovate only for new naming patterns; refresh snapshots if defaults change.
