from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.commands import cmd_explain
from springdocker.dockerfile import DockerfileOptions, build_dockerfile
from springdocker.errors import EXIT_OK, EXIT_USAGE


class ExplainCommandTests(unittest.TestCase):
    def test_explain_generated_dockerfile_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dockerfile = root / "Dockerfile.generated"
            dockerfile.write_text(
                build_dockerfile(DockerfileOptions(build_tool="maven", java_version=25)),
                encoding="utf-8",
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = cmd_explain(root, "Dockerfile.generated", "json")
            self.assertEqual(code, EXIT_OK)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["build_tool"], "maven")
            self.assertEqual(payload["java_version"], 25)
            self.assertIn("jlink runtime", [feature["name"] for feature in payload["features"]])
            self.assertIn("read-only filesystem ready", [feature["name"] for feature in payload["features"]])
            self.assertIn("multi-architecture build", [feature["name"] for feature in payload["features"]])
            self.assertEqual(
                payload["jlink_modules"]["baseline"],
                ["java.desktop", "java.logging", "java.naming"],
            )
            self.assertEqual(payload["jlink_modules"]["curated"], [])
            feature_names = [feature["name"] for feature in payload["features"]]
            self.assertIn("jlink baseline modules", feature_names)
            self.assertNotIn("must-have modules", feature_names)

    def test_explain_distinguishes_baseline_and_curated_modules(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dockerfile = root / "Dockerfile.generated"
            dockerfile.write_text(
                build_dockerfile(
                    DockerfileOptions(
                        build_tool="maven",
                        java_version=25,
                        must_have_modules=("jdk.crypto.ec",),
                    )
                ),
                encoding="utf-8",
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = cmd_explain(root, "Dockerfile.generated", "json")
            self.assertEqual(code, EXIT_OK)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(
                payload["jlink_modules"]["baseline"],
                ["java.desktop", "java.logging", "java.naming"],
            )
            self.assertEqual(payload["jlink_modules"]["curated"], ["jdk.crypto.ec"])
            feature_names = [feature["name"] for feature in payload["features"]]
            self.assertIn("jlink baseline modules", feature_names)
            self.assertIn("must-have modules", feature_names)

    def test_explain_generated_dockerfile_table(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dockerfile = root / "Dockerfile.generated"
            dockerfile.write_text(
                build_dockerfile(DockerfileOptions(build_tool="gradle", java_version=25)),
                encoding="utf-8",
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = cmd_explain(root, "Dockerfile.generated", "table")
            self.assertEqual(code, EXIT_OK)
            output = stdout.getvalue()
            self.assertIn("| Field | Value |", output)
            self.assertIn("BuildKit cache", output)
            self.assertIn("| Jlink baseline modules | java.desktop, java.logging, java.naming |", output)
            self.assertIn("| Curated must-have modules | - |", output)

    def test_explain_manual_dockerfile_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manual = root / "Dockerfile.generated"
            manual.write_text("FROM alpine:3.20\n", encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = cmd_explain(root, "Dockerfile.generated", "json")
            self.assertEqual(code, EXIT_OK)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["stage_count"], 1)

    def test_explain_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = cmd_explain(root, "Dockerfile.generated", "table")
            self.assertEqual(code, EXIT_USAGE)
            self.assertEqual(stdout.getvalue(), "")

    def test_explain_distroless_output_mentions_distroless(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dockerfile = root / "Dockerfile.generated"
            dockerfile.write_text(
                build_dockerfile(DockerfileOptions(build_tool="maven", runtime_image="distroless", use_jlink=False)),
                encoding="utf-8",
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = cmd_explain(root, "Dockerfile.generated", "json")
            self.assertEqual(code, EXIT_OK)
            payload = json.loads(stdout.getvalue())
            self.assertIn("distroless runtime", [feature["name"] for feature in payload["features"]])


if __name__ == "__main__":
    unittest.main()
