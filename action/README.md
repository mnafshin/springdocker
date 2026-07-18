# springdocker GitHub Action

Composite Action that installs [springdocker](https://pypi.org/project/springdocker/), regenerates the Dockerfile from `.springdocker.toml`, and fails the job when config drift is detected.

## Usage

```yaml
name: Dockerfile SSOT
on: [pull_request, push]
jobs:
  dockerfile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: mnafshin/springdocker/action@v1
        with:
          project-root: .
          dockerfile: Dockerfile.generated
          # Optional: pin the CLI version (setup --ci does this automatically)
          # springdocker-version: "1.2.0"
```

Or generate this workflow locally:

```bash
springdocker setup --ci
# existing project:
springdocker setup --ci-only
```

Generated workflows install the latest PyPI `springdocker` by default. Add `springdocker-version` under `with:` to pin.

## Inputs

| Input | Default | Description |
|---|---|---|
| `project-root` | `.` | Spring Boot project root |
| `dockerfile` | `Dockerfile.generated` | Dockerfile path relative to project root |
| `build-tool` | _(empty)_ | `maven` or `gradle`; empty = auto-detect |
| `springdocker-version` | _(empty)_ | Pin PyPI `springdocker` version; empty = latest |
| `python-version` | `3.11` | Python on the runner |
| `generate` | `true` | Run `dockerfile generate` |
| `check-config-drift` | `true` | Run `verify --check-config-drift` |

## Marketplace / versioning

Reference this Action by path (works on any tagged release of this repository):

```text
mnafshin/springdocker/action@v1
mnafshin/springdocker/action@v1.2.0
```

Publish a GitHub Release that includes this `action/` directory. Keep a moving `v1` major tag for consumers. Full marketplace listing can use the same release; the Action metadata lives in `action/action.yml` (path-based `uses:`).

Requires committed `.springdocker.toml` and (when `include_embedded_sbom = true`) an `sbom.spdx.json` in the consumer repository. See [docs/adopt.md](../docs/adopt.md).
