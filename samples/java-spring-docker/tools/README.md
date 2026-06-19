# Dockerfile setup

Use the config-first `springdocker` workflow instead of the retired wizard script.

```bash
# Interactive: writes [dockerfile] in .springdocker.toml
springdocker configure --project-root .

# CI / repeat runs: reads config only
springdocker dockerfile generate --project-root .
```

## Retired script

`tools/dockerfile_wizard.py` previously generated Dockerfiles interactively. It now prints
migration guidance and exits. Equivalent options live in `.springdocker.toml` and can be set
via `springdocker configure` or edited directly.

See [`cli/README.md`](../../cli/README.md#config-first-workflow) for flags, profiles, and precedence.
