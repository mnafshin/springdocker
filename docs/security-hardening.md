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

This repository automates baseline supply-chain controls in GitHub Actions:

- CI generates and publishes an SPDX SBOM artifact (`supply-chain` job).
- CI runs a **blocking** Trivy filesystem scan for unfixed **CRITICAL** vulnerabilities on every push and pull request. The job fails when CRITICAL issues are found; HIGH and below are not gated in that job.
- The release workflow signs build artifacts with keyless Cosign and emits provenance attestations.

### Trivy policy (repository CI vs `springdocker verify`)

| Surface | Scope | Severities | Blocks CI / exit code |
|---|---|---|---|
| GitHub Actions `supply-chain` job | Full repository checkout | CRITICAL only | **Yes** — unfixed CRITICAL fails the job |
| `springdocker verify` (optional tool) | Dockerfile build context by default (`--trivy-scan-project-root` for full tree) | HIGH, CRITICAL | Only when you run `verify` with `trivy` installed |

The repository scan and `verify` serve different purposes: CI guards the whole tree for catastrophic issues; `verify` is an opt-in, container-focused gate teams can add to their own pipelines.
