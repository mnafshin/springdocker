from __future__ import annotations

import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.cli import build_parser, main
from springdocker.commands import cmd_configure
from springdocker.config import load_config, resolve_dockerfile_generate_config
from springdocker.configure_wizard import run_configure_wizard


class ConfigureWizardTests(unittest.TestCase):
    def test_run_configure_wizard_writes_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project></project>", encoding="utf-8")
            config_path = root / ".springdocker.toml"
            with patch("springdocker.configure_wizard.ask_choice", return_value="production-balanced"):
                with patch("springdocker.configure_wizard.ask_bool", return_value=True):
                    run_configure_wizard(root, config_path)
            self.assertTrue(config_path.exists())
            text = config_path.read_text("utf-8")
            self.assertIn("[dockerfile]", text)
            self.assertIn('profile = "production-balanced"', text)
            self.assertIn('runtime_image = "distroless"', text)

    def test_cmd_configure_requires_force_when_config_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project></project>", encoding="utf-8")
            config_path = root / ".springdocker.toml"
            config_path.write_text("[project]\nbuild_tool = \"maven\"\n", encoding="utf-8")
            stderr = StringIO()
            with patch("sys.stderr", stderr):
                code = cmd_configure(root, None, config_path, force=False, generate_after=False)
            self.assertNotEqual(code, 0)
            self.assertIn("--force", stderr.getvalue())


class ConfigureCliTests(unittest.TestCase):
    def test_configure_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["configure", "--force", "--generate"])
        self.assertEqual(args.command, "configure")
        self.assertTrue(args.force)
        self.assertTrue(args.generate)

    def test_configure_end_to_end_with_mocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project></project>", encoding="utf-8")
            with patch("springdocker.configure_wizard.ask_choice", return_value="production-balanced"):
                with patch("springdocker.configure_wizard.ask_bool", return_value=True):
                    code = main(["configure", "--project-root", str(root), "--force"])
            self.assertEqual(code, 0)
            config_path = root / ".springdocker.toml"
            loaded = load_config(config_path)
            resolved = resolve_dockerfile_generate_config(*([None] * 23), loaded)
            self.assertEqual(resolved.runtime_image, "distroless")
            self.assertEqual(resolved.profile, "production-balanced")


if __name__ == "__main__":
    unittest.main()
