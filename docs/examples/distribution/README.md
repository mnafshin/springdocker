# Distribution templates (roadmap)

Starter manifests for **unshipped** channels. **Shipped path is PyPI** — see [cli install](../../../cli/README.md#install) and [ADR 0006](../../adr/0006-pypi-first-distribution.md).

| File | Purpose |
|---|---|
| `homebrew-formula.rb` | Homebrew formula from GitHub source tag via pip |
| `scoop-manifest.json` | Scoop manifest (Windows zip not in release CI yet) |
| `standalone-binary.sh` | Linux amd64 tarball wrapper (not in release CI yet) |

## Maintainer: bump on each release

After bumping `project.version` in `pyproject.toml` and tagging `vX.Y.Z`:

1. **`scoop-manifest.json`** — `"version"` and URL tag segment
2. **`homebrew-formula.rb`** — `url` + `sha256` for the source tarball
3. **`standalone-binary.sh`** — default `SPRINGDOCKER_VERSION`

Release workflow publishes **PyPI sdist/wheel only**. Replace `REPLACE_WITH_*` checksums when adopting a real tap.

```bash
grep '^version = ' pyproject.toml
grep -E 'version|v[0-9]|SPRINGDOCKER_VERSION' docs/examples/distribution/*
```
