# Distribution templates (examples)

Starter manifests for **roadmap** channels — not wired into CI today. The shipped release path is **PyPI** (see [docs/distribution.md](../../distribution.md)).

| File | Purpose |
|---|---|
| `homebrew-formula.rb` | Homebrew formula installing from GitHub source tag via pip |
| `scoop-manifest.json` | Scoop manifest (expects a published Windows zip — not built in release CI yet) |
| `standalone-binary.sh` | Wrapper downloading a Linux amd64 tarball (not built in release CI yet) |

## Maintainer: bump on each release

After bumping `project.version` in `pyproject.toml` and tagging `vX.Y.Z`:

1. **`scoop-manifest.json`** — set top-level `"version"` and the `vX.Y.Z` segment in the download URL.
2. **`homebrew-formula.rb`** — set `url` to `https://github.com/mnafshin/springdocker/archive/refs/tags/vX.Y.Z.tar.gz` and update `sha256` after verifying the tarball.
3. **`standalone-binary.sh`** — update the default in `SPRINGDOCKER_VERSION:-X.Y.Z` (or export `SPRINGDOCKER_VERSION` when testing).

Release workflow (`.github/workflows/release.yml`) publishes **Python sdist/wheel to PyPI** only. Scoop/standalone URLs are placeholders until native archives are added to the release pipeline.

Quick check:

```bash
grep '^version = ' pyproject.toml
grep -E 'version|v[0-9]|SPRINGDOCKER_VERSION' docs/examples/distribution/*
```
