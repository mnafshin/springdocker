from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.dockerfile import DockerfileOptions
from springdocker.plugins import (
    apply_dockerfile_mutators,
    detect_build_tool_from_plugins,
    register_command_plugins,
    render_recipe_from_plugins,
    render_verify_with_plugins,
)


class _EntryPoint:
    def __init__(self, name: str, loaded) -> None:  # type: ignore[no-untyped-def]
        self.name = name
        self._loaded = loaded

    def load(self):  # type: ignore[no-untyped-def]
        return self._loaded


class _AppendingPlugin:
    name = "append-label"

    def mutate_dockerfile(self, dockerfile_text: str, options: DockerfileOptions) -> str:
        return dockerfile_text + f'\nLABEL org.example.java="{options.java_version}"\n'


class _FailingPlugin:
    name = "broken-plugin"

    def mutate_dockerfile(self, dockerfile_text: str, options: DockerfileOptions) -> str:
        raise RuntimeError("boom")


class _ProjectDetectorMaven:
    def detect_build_tool(self, root) -> str:  # type: ignore[no-untyped-def]
        del root
        return "maven"


class _ProjectDetectorGradle:
    def detect_build_tool(self, root) -> str:  # type: ignore[no-untyped-def]
        del root
        return "gradle"


def _recipe_renderer(options: DockerfileOptions) -> str:
    return f"FROM base\n# {options.recipe}\n"


class _RegisterCommand:
    def register(self, subparsers) -> None:  # type: ignore[no-untyped-def]
        del subparsers


def _render_verify(outcome) -> str:  # type: ignore[no-untyped-def]
    return "ok" if not outcome.failed else "failed"


class PluginTests(unittest.TestCase):
    def test_applies_discovered_mutator(self) -> None:
        options = DockerfileOptions(build_tool="maven", java_version=21)
        with patch("springdocker.plugins._iter_entry_points", return_value=[_EntryPoint("append-label", _AppendingPlugin)]):
            result = apply_dockerfile_mutators("FROM base\n", options)
        self.assertIn('LABEL org.example.java="21"', result.dockerfile_text)
        self.assertEqual(result.warnings, ())

    def test_isolates_plugin_failures(self) -> None:
        options = DockerfileOptions(build_tool="maven")
        with patch("springdocker.plugins._iter_entry_points", return_value=[_EntryPoint("broken", _FailingPlugin)]):
            result = apply_dockerfile_mutators("FROM base\n", options)
        self.assertEqual(result.dockerfile_text, "FROM base\n")
        self.assertIn("plugin 'broken' failed", result.warnings[0])

    def test_detect_build_tool_from_plugins_returns_single_value(self) -> None:
        with patch(
            "springdocker.plugins._iter_entry_points",
            return_value=[_EntryPoint("p1", _ProjectDetectorMaven)],
        ):
            self.assertEqual(detect_build_tool_from_plugins(root=None), "maven")

    def test_detect_build_tool_from_plugins_rejects_conflicts(self) -> None:
        with patch(
            "springdocker.plugins._iter_entry_points",
            return_value=[_EntryPoint("p1", _ProjectDetectorMaven), _EntryPoint("p2", _ProjectDetectorGradle)],
        ), self.assertRaises(ValueError):
            detect_build_tool_from_plugins(root=None)

    def test_recipe_renderer_plugin(self) -> None:
        options = DockerfileOptions(build_tool="maven", recipe="acme")
        with patch("springdocker.plugins._iter_entry_points", return_value=[_EntryPoint("acme", _recipe_renderer)]):
            rendered = render_recipe_from_plugins("acme", options)
        self.assertTrue(rendered.handled)
        self.assertEqual(rendered.rendered, "FROM base\n# acme\n")
        self.assertEqual(rendered.warnings, ())

    def test_verify_renderer_plugin(self) -> None:
        class _Outcome:
            failed = False

        with patch("springdocker.plugins._iter_entry_points", return_value=[_EntryPoint("acme-json", _render_verify)]):
            rendered = render_verify_with_plugins("acme-json", _Outcome())
        self.assertTrue(rendered.handled)
        self.assertEqual(rendered.rendered, "ok")

    def test_register_command_plugins_returns_warnings(self) -> None:
        with patch("springdocker.plugins._iter_entry_points", return_value=[_EntryPoint("ok", _RegisterCommand)]):
            warnings = register_command_plugins(subparsers=object())
        self.assertEqual(warnings, ())


if __name__ == "__main__":
    unittest.main()
