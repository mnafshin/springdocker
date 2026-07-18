from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.ci_workflow import (
    action_uses_ref,
    render_dockerfile_ssot_workflow,
    write_dockerfile_ssot_workflow,
)
from springdocker.cli import build_parser, main
from springdocker.commands import cmd_setup


class CiWorkflowTests(unittest.TestCase):
    def test_action_uses_ref_major(self) -> None:
        self.assertEqual(action_uses_ref(package_version="1.2.0"), "mnafshin/springdocker/action@v1")
        self.assertEqual(action_uses_ref(package_version="2.0.0"), "mnafshin/springdocker/action@v2")

    def test_render_includes_action_and_pin(self) -> None:
        text = render_dockerfile_ssot_workflow(
            dockerfile="Dockerfile.generated",
            build_tool="maven",
            springdocker_version="1.2.0",
        )
        self.assertIn("mnafshin/springdocker/action@v1", text)
        self.assertIn('springdocker-version: "1.2.0"', text)
        self.assertIn("build-tool: maven", text)
        self.assertIn("Dockerfile.generated", text)

    def test_render_omits_version_pin_by_default(self) -> None:
        text = render_dockerfile_ssot_workflow(dockerfile="Dockerfile.generated")
        self.assertIn("mnafshin/springdocker/action@v1", text)
        self.assertNotIn("springdocker-version:", text)

    def test_write_workflow_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = write_dockerfile_ssot_workflow(root, dockerfile="Dockerfile.prod")
            self.assertEqual(path, root / ".github" / "workflows" / "dockerfile.yml")
            self.assertTrue(path.is_file())
            self.assertIn("Dockerfile.prod", path.read_text(encoding="utf-8"))

    def test_write_workflow_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_dockerfile_ssot_workflow(root)
            with self.assertRaises(FileExistsError):
                write_dockerfile_ssot_workflow(root)


class SetupCiTests(unittest.TestCase):
    def test_setup_parse_ci_flags(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["setup", "--ci", "--ci-only", "--force"])
        self.assertTrue(args.ci)
        self.assertTrue(args.ci_only)
        self.assertTrue(args.force)

    def test_setup_ci_writes_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            code = cmd_setup(root, None, root / ".springdocker.toml", ci=True)
            self.assertEqual(code, 0)
            workflow = root / ".github" / "workflows" / "dockerfile.yml"
            self.assertTrue(workflow.is_file())
            self.assertTrue((root / "Dockerfile.generated").is_file())

    def test_setup_ci_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code = cmd_setup(root, None, root / ".springdocker.toml", ci_only=True)
            self.assertEqual(code, 0)
            self.assertTrue((root / ".github" / "workflows" / "dockerfile.yml").is_file())
            self.assertFalse((root / ".springdocker.toml").exists())

    def test_setup_ci_only_cli(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            code = main(["setup", "--project-root", str(root), "--ci-only"])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
