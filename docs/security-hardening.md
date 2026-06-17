# Security hardening

`springdocker` generated Dockerfiles already favor safer defaults:

- non-root runtime user
- writable `/tmp`
- distroless runtime support
- container-friendly JVM flags

## Runtime recommendations

Use the generated image with:

```bash
docker run --read-only --cap-drop=ALL --security-opt=no-new-privileges --tmpfs /tmp app:latest
```

## Why this matters

- `--read-only` limits accidental writes.
- `--cap-drop=ALL` reduces Linux capability exposure.
- `--security-opt=no-new-privileges` prevents privilege escalation.
- `--tmpfs /tmp` keeps the JVM temp directory writable.

## Supply-chain hygiene

- Pin base images by digest where the generator catalog provides them ([`digest-pin-runbook.md`](digest-pin-runbook.md)).
- Generate an SBOM in CI.
- Sign images before release.
- Scan images and dependencies regularly.

## Current scope

This repository now automates baseline supply-chain controls in GitHub Actions:

- CI generates and publishes an SPDX SBOM artifact.
- CI runs a CRITICAL-severity vulnerability scan gate.
- The release workflow signs build artifacts with keyless Cosign and emits provenance attestations.
