from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.cli import build_parser, main
from springdocker.commands import cmd_setup
from springdocker.configure_wizard import apply_profile_to_config


class SetupCommandTests(unittest.TestCase):
    def test_setup_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["setup", "--profile", "simplest", "--force", "--verify", "--output", "Dockerfile.prod"]
        )
        self.assertEqual(args.command, "setup")
        self.assertEqual(args.profile, "simplest")
        self.assertTrue(args.force)
        self.assertTrue(args.verify)
        self.assertEqual(args.output, "Dockerfile.prod")
        self.assertFalse(args.interactive)

    def test_apply_profile_to_config_writes_production_balanced(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            cfg = root / ".springdocker.toml"
            resolved, warning = apply_profile_to_config(root, cfg, force=False)
            self.assertIsNone(warning)
            self.assertEqual(resolved.profile, "production-balanced")
            self.assertEqual(resolved.runtime_image, "distroless")
            text = cfg.read_text(encoding="utf-8")
            self.assertIn('profile = "production-balanced"', text)
            self.assertIn('runtime_image = "distroless"', text)

    def test_setup_writes_config_and_dockerfile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text(
                "<project><properties><java.version>17</java.version></properties></project>",
                encoding="utf-8",
            )
            (root / "src/main/resources").mkdir(parents=True)
            (root / "src/main/resources/application.properties").write_text("server.port=8080\n", encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = cmd_setup(root, None, root / ".springdocker.toml")
            self.assertEqual(code, 0)
            self.assertTrue((root / ".springdocker.toml").exists())
            self.assertTrue((root / "Dockerfile.generated").exists())
            self.assertIn("wrote config:", stdout.getvalue())
            self.assertIn("wrote dockerfile:", stdout.getvalue())
            self.assertIn("next:", stdout.getvalue())

    def test_setup_requires_force_when_config_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            cfg = root / ".springdocker.toml"
            cfg.write_text('[project]\nbuild_tool = "maven"\n', encoding="utf-8")
            code = cmd_setup(root, None, cfg, force=False)
            self.assertEqual(code, 2)

    def test_setup_force_overwrites_dockerfile_section(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            cfg = root / ".springdocker.toml"
            cfg.write_text('[project]\nbuild_tool = "maven"\n\n[dockerfile]\nruntime_image = "temurin"\n', encoding="utf-8")
            code = cmd_setup(root, None, cfg, force=True, profile="simplest")
            self.assertEqual(code, 0)
            text = cfg.read_text(encoding="utf-8")
            self.assertIn('profile = "simplest"', text)
            self.assertIn('runtime_image = "temurin"', text)

    def test_setup_cli_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            code = main(["setup", "--project-root", str(root)])
            self.assertEqual(code, 0)
            self.assertTrue((root / "Dockerfile.generated").exists())

    def test_setup_verify_writes_placeholder_sbom(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            with patch("springdocker.commands.cmd_verify", return_value=0) as verify:
                code = cmd_setup(root, None, root / ".springdocker.toml", verify=True)
            self.assertEqual(code, 0)
            verify.assert_called_once()
            self.assertTrue((root / "sbom.spdx.json").exists())

    def test_apply_profile_rejects_custom(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            with self.assertRaises(ValueError):
                apply_profile_to_config(root, root / ".springdocker.toml", profile="custom")

    def test_setup_interactive_delegates_to_configure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            with patch("springdocker.commands.cmd_configure", return_value=0) as configure:
                code = cmd_setup(root, None, root / ".springdocker.toml", interactive=True)
            self.assertEqual(code, 0)
            configure.assert_called_once()
            kwargs = configure.call_args.kwargs
            self.assertTrue(kwargs["force"])
            self.assertTrue(kwargs["generate_after"])


if __name__ == "__main__":
    unittest.main()
