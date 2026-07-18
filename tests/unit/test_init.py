from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.commands import cmd_init


class InitCommandTests(unittest.TestCase):
    def test_init_writes_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            cfg = root / ".springdocker.toml"
            code = cmd_init(root, None, cfg, profile="full", force=False, print_only=False)
            self.assertEqual(code, 0)
            self.assertTrue(cfg.exists())
            text = cfg.read_text(encoding="utf-8")
            self.assertIn('build_tool = "maven"', text)
            self.assertIn('profile = "full"', text)
            self.assertIn("jlink_baseline_modules", text)

    def test_init_prints_dockerfile_generate_hint(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            cfg = root / ".springdocker.toml"
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = cmd_init(root, None, cfg, profile="quick", force=False, print_only=False)
            self.assertEqual(code, 0)
            self.assertIn("next: springdocker setup   # or: springdocker dockerfile generate", stdout.getvalue())

    def test_init_requires_force_when_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            cfg = root / ".springdocker.toml"
            cfg.write_text("[project]\n", encoding="utf-8")
            code = cmd_init(root, None, cfg, profile="quick", force=False, print_only=False)
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
