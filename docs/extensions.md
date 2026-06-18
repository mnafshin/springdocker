# Extension model

`springdocker` supports runtime plugins through six Python entry-point groups. Architecture decision record: [`adr/0001-plugin-architecture.md`](adr/0001-plugin-architecture.md).

## Extension points

| Entry-point group | Contract | Used by |
|---|---|---|
| `springdocker.dockerfile_mutators` | `mutate_dockerfile(dockerfile_text, options) -> str` | Post-process generated Dockerfiles |
| `springdocker.project_detectors` | `detect_build_tool(project_root) -> "maven" \| "gradle" \| None` | Build-tool detection override for exotic monorepos |
| `springdocker.recipes` | entry-point name is recipe name; callable returns Dockerfile text | Custom `dockerfile generate --recipe ...` |
| `springdocker.verifiers` | `verify(context) -> (status, detail)` or dict payload | Extra checks in `verify` command |
| `springdocker.verify_renderers` | entry-point name is output format; callable `render(outcome) -> str` | Custom `verify --format ...` renderers |
| `springdocker.commands` | `register(subparsers)` and parser `set_defaults(_plugin_handler=...)` | Add top-level CLI commands |

For multi-module Maven reactors and Gradle composites, start with [`project-detection.md`](project-detection.md) — built-in inspect reports `layout` and `spring_boot_modules`, and `project_detectors` plugins cover layouts static parsing cannot handle.

## Failure handling

- Plugin failures are isolated per plugin.
- The command keeps running with built-in behavior whenever possible.
- Warnings are emitted for failed plugin invocations.
- Set `SPRINGDOCKER_DISABLE_PLUGINS=1` to disable all plugin groups.

## Reference plugins

See:

- `docs/examples/extensions/custom_dockerfile_mutator.py`
- `docs/examples/extensions/custom_project_detector.py`
- `docs/examples/extensions/maven_reactor_project_detector.py`
- `docs/examples/extensions/gradle_monorepo_project_detector.py`
- `docs/examples/extensions/custom_recipe.py`
- `docs/examples/extensions/custom_verifier.py`
- `docs/examples/extensions/custom_verify_renderer.py`
- `docs/examples/extensions/custom_command.py`

## Packaging example

```toml
[project.entry-points."springdocker.dockerfile_mutators"]
company-label = "acme_plugins.mutators:CompanyLabelMutator"

[project.entry-points."springdocker.project_detectors"]
mono-repo = "acme_plugins.detectors:detect_build_tool"

[project.entry-points."springdocker.recipes"]
acme-jvm = "acme_plugins.recipes:render_recipe"

[project.entry-points."springdocker.verifiers"]
license = "acme_plugins.verifiers:verify"

[project.entry-points."springdocker.verify_renderers"]
acme-json = "acme_plugins.renderers:render"

[project.entry-points."springdocker.commands"]
acme-doctor = "acme_plugins.commands:register"
```
