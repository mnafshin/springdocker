from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.commands import cmd_verify
from springdocker.config import load_config
from springdocker.config_audit import resolve_dockerfile_audit_config
from springdocker.errors import EXIT_FAILURE, EXIT_OK, EXIT_USAGE
from springdocker.services.dockerfile_service import render_dockerfile_text_from_config


class VerifyCommandTests(unittest.TestCase):
    def test_verify_missing_dockerfile_returns_usage(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stderr = StringIO()
            with redirect_stderr(stderr):
                code = cmd_verify(root, "Dockerfile.generated", None, None, "json", None)
            self.assertEqual(code, EXIT_USAGE)
            self.assertIn("missing Dockerfile", stderr.getvalue())

    def test_verify_returns_failure_when_sbom_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dockerfile = root / "Dockerfile.generated"
            dockerfile.write_text("FROM scratch\n", encoding="utf-8")
            stdout = StringIO()
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                redirect_stdout(stdout),
            ):
                code = cmd_verify(root, "Dockerfile.generated", None, None, "json", None)
            self.assertEqual(code, EXIT_FAILURE)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["overall"], "failed")

    def test_verify_returns_ok_when_only_skipped_checks_remain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dockerfile = root / "Dockerfile.generated"
            dockerfile.write_text("FROM scratch\n", encoding="utf-8")
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")
            stdout = StringIO()
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                redirect_stdout(stdout),
            ):
                code = cmd_verify(root, "Dockerfile.generated", None, None, "table", None)
            self.assertEqual(code, EXIT_OK)
            self.assertIn("| overall | passed |", stdout.getvalue())

    def test_verify_writes_report_to_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dockerfile = root / "Dockerfile.generated"
            dockerfile.write_text("FROM scratch\n", encoding="utf-8")
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")
            stdout = StringIO()
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                redirect_stdout(stdout),
            ):
                code = cmd_verify(root, "Dockerfile.generated", None, None, "sarif", "reports/verify.sarif")
            self.assertEqual(code, EXIT_OK)
            report = root / "reports" / "verify.sarif"
            self.assertTrue(report.exists())
            self.assertIn("wrote verification report", stdout.getvalue())

    def test_verify_check_config_drift_passes_for_config_generated_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".springdocker.toml").write_text(
                "[project]\n"
                'build_tool = "maven"\n\n'
                "[dockerfile]\n"
                'output = "Dockerfile.generated"\n'
                'runtime_image = "alpine"\n',
                encoding="utf-8",
            )
            dockerfile = root / "Dockerfile.generated"
            loaded = load_config(root / ".springdocker.toml")
            config = resolve_dockerfile_audit_config(root, "maven", dockerfile, loaded)
            dockerfile.write_text(
                render_dockerfile_text_from_config(root, config, "maven"),
                encoding="utf-8",
            )
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")
            stdout = StringIO()
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                redirect_stdout(stdout),
            ):
                code = cmd_verify(
                    root,
                    "Dockerfile.generated",
                    None,
                    None,
                    "json",
                    None,
                    check_config_drift=True,
                    build_tool="maven",
                )
            self.assertEqual(code, EXIT_OK)
            payload = json.loads(stdout.getvalue())
            checks = {item["name"]: item for item in payload["results"]}
            self.assertEqual(checks["config-drift"]["status"], "passed")
            self.assertEqual(checks["config-embedded-sbom"]["status"], "passed")
            self.assertEqual(checks["config-non-root"]["status"], "passed")

    def test_verify_check_config_drift_fails_on_manual_edit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".springdocker.toml").write_text(
                "[project]\n"
                'build_tool = "maven"\n\n'
                "[dockerfile]\n"
                'output = "Dockerfile.generated"\n',
                encoding="utf-8",
            )
            (root / "Dockerfile.generated").write_text("FROM scratch\n", encoding="utf-8")
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")
            stdout = StringIO()
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                redirect_stdout(stdout),
            ):
                code = cmd_verify(
                    root,
                    "Dockerfile.generated",
                    None,
                    None,
                    "json",
                    None,
                    check_config_drift=True,
                    build_tool="maven",
                )
            self.assertEqual(code, EXIT_FAILURE)
            payload = json.loads(stdout.getvalue())
            checks = {item["name"]: item for item in payload["results"]}
            self.assertEqual(checks["config-drift"]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
