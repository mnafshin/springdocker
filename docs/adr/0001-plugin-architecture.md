# ADR 0001: Plugin architecture

## Status

Accepted (amended 2026-06 — expanded from mutator-only to six entry-point groups; closes [#78](https://github.com/mnafshin/springdocker/issues/78))

## Context

The CLI needs extension hooks without turning every command into a bespoke plugin framework. The first
implementation added a single Dockerfile mutator group for post-processing generated output.

Since then, the codebase gained five more entry-point groups for project detection, custom recipes,
verify checks, verify output formats, and top-level CLI commands. The authoritative contract table lives
in [`docs/extensions.md`](../extensions.md); this ADR records the architectural decision behind it.

Implementation: `src/springdocker/plugins.py`.

## Decision

Use **six** Python entry-point groups, discovered at runtime via `importlib.metadata.entry_points`.
Each group has a narrow contract and is invoked from a specific command path:

| Entry-point group | Contract (summary) | Invoked by |
|---|---|---|
| `springdocker.dockerfile_mutators` | `mutate_dockerfile(text, options) -> str` | After built-in Dockerfile render (`dockerfile generate`) |
| `springdocker.project_detectors` | `detect_build_tool(root) -> "maven" \| "gradle" \| None` | Project detection before doctor / generate / inspect |
| `springdocker.recipes` | Entry-point **name** is the recipe id; renderer returns Dockerfile text | `dockerfile generate --recipe <name>` when name is not a built-in recipe |
| `springdocker.verifiers` | `verify(context) -> status payload` | `verify` command (alongside built-in checks) |
| `springdocker.verify_renderers` | Entry-point **name** is the format id; `render(outcome) -> str` | `verify --format <name>` when format is not built-in |
| `springdocker.commands` | `register(subparsers)` registers a subcommand with `_plugin_handler` | CLI startup (`cli.py` parser construction) |

Built-in recipes (`jvm-balanced`, `spring-aot`, `native-aot`) and built-in verify formats are handled in
core code. Plugins extend or override only when an entry point matches the requested name (recipes,
renderers) or when the group is enumerated (mutators, detectors, verifiers, commands).

### Shared rules (all groups)

- **Isolated failures:** a broken plugin must not crash the host command when built-in behavior can continue.
- **Warnings, not silent drops:** failed plugin invocations surface as user-visible warnings (or registration warnings for command plugins).
- **Global disable:** `SPRINGDOCKER_DISABLE_PLUGINS=1` skips every group.
- **No required plugins:** the CLI must work with zero third-party entry points installed.
- **Deterministic order:** entry points within a group are sorted by name before invocation.

Reference implementations for each group are under `docs/examples/extensions/`.

## Consequences

- Downstream teams can customize Dockerfiles, detection, recipes, verify output, and CLI surface area without forking `springdocker`.
- The extension model stays **modular** — each group serves one command concern instead of a single mega-plugin interface.
- New extension surfaces require a new entry-point group (and ADR amendment), not ad hoc hooks scattered through commands.
- Documentation must keep [`docs/extensions.md`](../extensions.md) and this ADR in sync when groups or contracts change.

## References

- [`docs/extensions.md`](../extensions.md) — contract table, failure handling, packaging examples
- [`docs/project-detection.md`](../project-detection.md) — when to use `project_detectors`
- `src/springdocker/plugins.py` — discovery and dispatch
