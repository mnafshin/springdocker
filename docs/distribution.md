# Distribution

`springdocker` is published on **PyPI** as the primary distribution channel. Install it and run against your Spring Boot project — no repository clone required for the core CLI workflow.

## Shipped today

| Channel | Command | Notes |
|---|---|---|
| **PyPI (base)** | `pip install springdocker` | Dockerfile generate, explain, verify, init, configure, doctor |
| **PyPI + benchmarks** | `pip install 'springdocker[benchmark]'` | Adds `requests`; `benchmark run` still requires Docker |
| **pipx** | `pipx install springdocker` or `pipx install 'springdocker[benchmark]'` | Recommended isolated user install |
| **uv tool** | `uv tool install springdocker` | Same as pipx for uv users |

Upgrade: `pipx upgrade springdocker`, `uv tool upgrade springdocker`, or `pip install -U springdocker`.

See [README install](../README.md#install) and [cli/README.md](../cli/README.md#install).

## When to clone the repository

Clone [github.com/mnafshin/springdocker](https://github.com/mnafshin/springdocker) when you need:

- the benchmark harness under `samples/java-spring-docker/`
- presentation decks or pinned CI baseline CSVs
- an editable install for contributions

Decision record: [ADR 0006: PyPI-first distribution](adr/0006-pypi-first-distribution.md).

## Roadmap channels

These are not required for the primary PyPI path:

| Channel | Notes |
|---|---|
| Homebrew tap | macOS/Linux manifest-based install |
| Scoop | Windows manifest-based install |
| Standalone binary | For hosts without Python |
| Dockerized CLI runtime | Hermetic CI invocations |

Template files for some of these live under `docs/examples/distribution/` (`homebrew-formula.rb`, `scoop-manifest.json`, `standalone-binary.sh`). See [`docs/examples/distribution/README.md`](../examples/distribution/README.md) for file roles and bump checklist.

## Release alignment

- Keep the published PyPI version aligned with `pyproject.toml` / git tags (`vMAJOR.MINOR.PATCH`).
- Generate release artifacts from tagged builds (see `.github/workflows/release.yml`).
- **Bump example templates** under `docs/examples/distribution/` on each release so version strings and tag URLs stay in sync with `pyproject.toml` (currently **1.0.4**).

### Template variables

| Template | Version source | Download URL pattern |
|---|---|---|
| `homebrew-formula.rb` | tag in `url` | `.../archive/refs/tags/vX.Y.Z.tar.gz` (source tarball — published with tags) |
| `scoop-manifest.json` | `"version"` field | `.../releases/download/vX.Y.Z/springdocker-windows-amd64.zip` (placeholder until CI ships zip) |
| `standalone-binary.sh` | `SPRINGDOCKER_VERSION` env, default `1.0.4` | `.../releases/download/vX.Y.Z/springdocker-linux-amd64.tar.gz` (placeholder until CI ships tarball) |

Replace `REPLACE_WITH_*` checksum placeholders when adopting a manifest for a real tap or bucket. Until standalone archives exist in GitHub Releases, prefer **pipx** / **PyPI** for end users.
