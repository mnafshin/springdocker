from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.test_support import ROOT, add_src_to_path

add_src_to_path()

from springdocker.services.verify_service import (
    VerifyContext,
    VerifyOutcome,
    VerifyResult,
    _trivy_scan_targets,
    render_verify_json,
    render_verify_junit,
    render_verify_sarif,
    render_verify_table,
    run_verification,
)


class _Completed:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeEntry:
    def __init__(self, name: str, loader) -> None:
        self.name = name
        self.load = loader


def _urlopen_response(*, status: int = 200, body: bytes = b"") -> MagicMock:
    response = MagicMock()
    response.status = status
    response.read.return_value = body
    opener = MagicMock()
    opener.__enter__.return_value = response
    opener.__exit__.return_value = False
    return opener


def _context(
    root: Path,
    *,
    image: str | None = None,
    smoke_url: str | None = None,
) -> VerifyContext:
    dockerfile = root / "Dockerfile.generated"
    dockerfile.write_text("FROM scratch\n", encoding="utf-8")
    return VerifyContext(
        project_root=root,
        dockerfile_path=dockerfile,
        image=image,
        smoke_url=smoke_url,
    )


class VerifyServiceTests(unittest.TestCase):
    def test_run_verification_skips_external_tools_when_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch("springdocker.services.verify_service.shutil.which", return_value=None):
                outcome = run_verification(_context(root))
            skipped = {item.name: item for item in outcome.results if item.status == "skipped"}
            self.assertIn("hadolint", skipped)
            self.assertIn("trivy", skipped)
            self.assertEqual(skipped["hadolint"].detail, "hadolint not installed")
            self.assertEqual(skipped["trivy"].detail, "trivy not installed")
            self.assertIn("dive", skipped)
            self.assertEqual(skipped["dive"].detail, "no image provided")
            self.assertIn("cosign", skipped)
            self.assertEqual(skipped["cosign"].detail, "no image provided")
            self.assertIn("smoke", skipped)
            self.assertEqual(skipped["smoke"].detail, "no smoke URL provided")

    def test_run_verification_marks_missing_sbom_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch("springdocker.services.verify_service.shutil.which", return_value=None):
                outcome = run_verification(_context(root))
            sbom = next(item for item in outcome.results if item.name == "sbom")
            self.assertEqual(sbom.status, "failed")
            self.assertTrue(outcome.failed)

    def test_run_verification_passes_sbom_when_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")
            with patch("springdocker.services.verify_service.shutil.which", return_value=None):
                outcome = run_verification(_context(root))
            sbom = next(item for item in outcome.results if item.name == "sbom")
            self.assertEqual(sbom.status, "passed")
            self.assertFalse(outcome.failed)

    def test_run_verification_fails_on_invalid_sbom_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text("{not-json", encoding="utf-8")
            with patch("springdocker.services.verify_service.shutil.which", return_value=None):
                outcome = run_verification(_context(root))
            sbom = next(item for item in outcome.results if item.name == "sbom")
            self.assertEqual(sbom.status, "failed")
            self.assertIn("invalid SBOM JSON", sbom.detail)

    def test_run_verification_fails_when_sbom_missing_spdx_version(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"name": "demo"}), encoding="utf-8")
            with patch("springdocker.services.verify_service.shutil.which", return_value=None):
                outcome = run_verification(_context(root))
            sbom = next(item for item in outcome.results if item.name == "sbom")
            self.assertEqual(sbom.status, "failed")
            self.assertEqual(sbom.detail, "SBOM missing spdxVersion field")

    def test_run_verification_calls_tool_verifiers_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")

            with (
                patch("springdocker.services.verify_service.shutil.which", return_value="/usr/bin/fake"),
                patch("springdocker.services.verify_service.subprocess.run", return_value=_Completed()),
            ):
                outcome = run_verification(_context(root, image="demo:latest"))
            hadolint = next(item for item in outcome.results if item.name == "hadolint")
            trivy = next(item for item in outcome.results if item.name == "trivy")
            dive = next(item for item in outcome.results if item.name == "dive")
            cosign = next(item for item in outcome.results if item.name == "cosign")
            self.assertEqual(hadolint.status, "passed")
            self.assertEqual(trivy.status, "passed")
            self.assertIn("dockerfile build context", trivy.detail)
            self.assertEqual(dive.status, "passed")
            self.assertEqual(cosign.status, "passed")

    def test_trivy_scan_targets_default_to_dockerfile_build_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            service_dir = root / "service"
            service_dir.mkdir()
            dockerfile = service_dir / "Dockerfile.generated"
            dockerfile.write_text("FROM scratch\n", encoding="utf-8")
            (root / "other-module").mkdir()
            context = VerifyContext(
                project_root=root,
                dockerfile_path=dockerfile,
                image=None,
                smoke_url=None,
            )
            targets, label = _trivy_scan_targets(context)
            self.assertEqual(label, "dockerfile build context")
            self.assertEqual(set(targets), {dockerfile.resolve(), service_dir.resolve()})
            self.assertNotIn(root.resolve(), targets)

    def test_trivy_scan_targets_project_root_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dockerfile = root / "Dockerfile.generated"
            dockerfile.write_text("FROM scratch\n", encoding="utf-8")
            context = VerifyContext(
                project_root=root,
                dockerfile_path=dockerfile,
                image=None,
                smoke_url=None,
                trivy_scan_project_root=True,
            )
            targets, label = _trivy_scan_targets(context)
            self.assertEqual(label, "project root")
            self.assertEqual(targets, (root.resolve(),))

    def test_run_verification_trivy_uses_build_context_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            service_dir = root / "service"
            service_dir.mkdir()
            dockerfile = service_dir / "Dockerfile.generated"
            dockerfile.write_text("FROM scratch\n", encoding="utf-8")
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")
            context = VerifyContext(
                project_root=root,
                dockerfile_path=dockerfile,
                image=None,
                smoke_url=None,
            )
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value="/usr/bin/fake"),
                patch("springdocker.services.verify_service.subprocess.run", return_value=_Completed()) as run_mock,
            ):
                run_verification(context)
            trivy_calls = [call.args[0] for call in run_mock.call_args_list if call.args[0][0] == "trivy"]
            self.assertEqual(len(trivy_calls), 1)
            self.assertIn(str(dockerfile.resolve()), trivy_calls[0])
            self.assertIn(str(service_dir.resolve()), trivy_calls[0])
            self.assertNotIn(str(root.resolve()), trivy_calls[0])

    def test_run_verification_marks_tool_nonzero_exit_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")

            with (
                patch("springdocker.services.verify_service.shutil.which", return_value="/usr/bin/fake"),
                patch(
                    "springdocker.services.verify_service.subprocess.run",
                    return_value=_Completed(returncode=1, stderr="hadolint rule violated"),
                ),
            ):
                outcome = run_verification(_context(root))
            hadolint = next(item for item in outcome.results if item.name == "hadolint")
            self.assertEqual(hadolint.status, "failed")
            self.assertEqual(hadolint.detail, "hadolint rule violated")
            self.assertTrue(outcome.failed)

    def test_run_verification_smoke_passes_when_health_reports_up(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch(
                    "springdocker.services.verify_service.urllib.request.urlopen",
                    return_value=_urlopen_response(body=b'{"status":"UP"}'),
                ),
            ):
                outcome = run_verification(_context(root, smoke_url="http://127.0.0.1:8081/actuator/health"))
            smoke = next(item for item in outcome.results if item.name == "smoke")
            self.assertEqual(smoke.status, "passed")
            self.assertEqual(smoke.detail, "service reported UP")

    def test_run_verification_smoke_passes_without_up_marker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch(
                    "springdocker.services.verify_service.urllib.request.urlopen",
                    return_value=_urlopen_response(body=b"ok"),
                ),
            ):
                outcome = run_verification(_context(root, smoke_url="http://127.0.0.1:8081/"))
            smoke = next(item for item in outcome.results if item.name == "smoke")
            self.assertEqual(smoke.status, "passed")
            self.assertEqual(smoke.detail, "http status 200")

    def test_run_verification_smoke_fails_on_http_error_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch(
                    "springdocker.services.verify_service.urllib.request.urlopen",
                    return_value=_urlopen_response(status=503, body=b"down"),
                ),
            ):
                outcome = run_verification(_context(root, smoke_url="http://127.0.0.1:8081/actuator/health"))
            smoke = next(item for item in outcome.results if item.name == "smoke")
            self.assertEqual(smoke.status, "failed")
            self.assertEqual(smoke.detail, "http status 503")

    def test_run_verification_smoke_fails_on_connection_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch(
                    "springdocker.services.verify_service.urllib.request.urlopen",
                    side_effect=urllib.error.URLError("connection refused"),
                ),
            ):
                outcome = run_verification(_context(root, smoke_url="http://127.0.0.1:8081/actuator/health"))
            smoke = next(item for item in outcome.results if item.name == "smoke")
            self.assertEqual(smoke.status, "failed")
            self.assertIn("connection refused", smoke.detail)

    def test_run_verification_smoke_fails_on_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch(
                    "springdocker.services.verify_service.urllib.request.urlopen",
                    side_effect=TimeoutError("timed out"),
                ),
            ):
                outcome = run_verification(_context(root, smoke_url="http://127.0.0.1:8081/actuator/health"))
            smoke = next(item for item in outcome.results if item.name == "smoke")
            self.assertEqual(smoke.status, "failed")
            self.assertIn("timed out", smoke.detail)

    def test_run_verification_runs_plugin_verifier_tuple_result(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")

            def verify(_context) -> tuple[str, str]:
                return "passed", "policy ok"

            entry = _FakeEntry("acme", lambda: verify)
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch("springdocker.services.verify_service.iter_verifier_entry_points", return_value=[entry]),
            ):
                outcome = run_verification(_context(root))
            plugin = next(item for item in outcome.results if item.name == "plugin:acme")
            self.assertEqual(plugin.status, "passed")
            self.assertEqual(plugin.detail, "policy ok")

    def test_run_verification_runs_plugin_verifier_dict_result(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")

            class PolicyVerifier:
                def verify(self, _context) -> dict[str, str]:
                    return {"status": "skipped", "detail": "not applicable"}

            entry = _FakeEntry("policy", lambda: PolicyVerifier)
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch("springdocker.services.verify_service.iter_verifier_entry_points", return_value=[entry]),
            ):
                outcome = run_verification(_context(root))
            plugin = next(item for item in outcome.results if item.name == "plugin:policy")
            self.assertEqual(plugin.status, "skipped")
            self.assertEqual(plugin.detail, "not applicable")

    def test_run_verification_marks_plugin_exception_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")

            def broken_loader():
                raise RuntimeError("plugin load failed")

            entry = _FakeEntry("broken", broken_loader)
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch("springdocker.services.verify_service.iter_verifier_entry_points", return_value=[entry]),
            ):
                outcome = run_verification(_context(root))
            plugin = next(item for item in outcome.results if item.name == "plugin:broken")
            self.assertEqual(plugin.status, "failed")
            self.assertIn("plugin load failed", plugin.detail)

    def test_run_verification_marks_invalid_plugin_payload_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")

            def verify(_context) -> tuple[str, str]:
                return "unknown", "bad status"

            entry = _FakeEntry("invalid", lambda: verify)
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch("springdocker.services.verify_service.iter_verifier_entry_points", return_value=[entry]),
            ):
                outcome = run_verification(_context(root))
            plugin = next(item for item in outcome.results if item.name == "plugin:invalid")
            self.assertEqual(plugin.status, "failed")
            self.assertIn("invalid plugin verifier status", plugin.detail)

    def test_run_verification_marks_invalid_plugin_dict_status_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")

            def verify(_context) -> dict[str, str]:
                return {"status": "bogus", "detail": "bad"}

            entry = _FakeEntry("invalid-dict", lambda: verify)
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch("springdocker.services.verify_service.iter_verifier_entry_points", return_value=[entry]),
            ):
                outcome = run_verification(_context(root))
            plugin = next(item for item in outcome.results if item.name == "plugin:invalid-dict")
            self.assertEqual(plugin.status, "failed")
            self.assertIn("invalid plugin verifier status", plugin.detail)

    def test_run_verification_marks_non_callable_plugin_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")

            class BrokenPlugin:
                pass

            entry = _FakeEntry("broken-shape", lambda: BrokenPlugin)
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch("springdocker.services.verify_service.iter_verifier_entry_points", return_value=[entry]),
            ):
                outcome = run_verification(_context(root))
            plugin = next(item for item in outcome.results if item.name == "plugin:broken-shape")
            self.assertEqual(plugin.status, "failed")
            self.assertIn("verifier plugin must define verify(context) or be callable", plugin.detail)

    def test_run_verification_marks_unsupported_plugin_return_type_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")

            def verify(_context) -> str:
                return "unexpected"

            entry = _FakeEntry("bad-return", lambda: verify)
            with (
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch("springdocker.services.verify_service.iter_verifier_entry_points", return_value=[entry]),
            ):
                outcome = run_verification(_context(root))
            plugin = next(item for item in outcome.results if item.name == "plugin:bad-return")
            self.assertEqual(plugin.status, "failed")
            self.assertIn("verifier plugin must return (status, detail) or a dict payload", plugin.detail)

    def test_render_verify_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")
            with patch("springdocker.services.verify_service.shutil.which", return_value=None):
                outcome = run_verification(_context(root))
            self.assertIn('"overall": "passed"', render_verify_json(outcome))
            self.assertIn("<testsuite", render_verify_junit(outcome))
            self.assertIn('"version": "2.1.0"', render_verify_sarif(outcome))
            table = render_verify_table(outcome)
            self.assertIn("| overall | passed |", table)

    def test_render_verify_junit_reports_failures_and_skips(self) -> None:
        outcome = VerifyOutcome(
            results=(
                VerifyResult(name="sbom", status="failed", detail="missing SBOM file", duration_ms=1),
                VerifyResult(name="hadolint", status="skipped", detail="hadolint not installed", duration_ms=2),
            )
        )
        junit = render_verify_junit(outcome)
        self.assertIn('failures="1"', junit)
        self.assertIn('skipped="1"', junit)
        self.assertIn('<failure message="missing SBOM file"/>', junit)
        self.assertIn('<skipped message="hadolint not installed"/>', junit)
        self.assertIn("| overall | failed |", render_verify_table(outcome))

    def test_config_drift_resolves_build_tool_from_config_for_mixed_markers(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "mixed-markers"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in ("pom.xml", "build.gradle", "gradlew"):
                (root / name).write_text((fixture / name).read_text(encoding="utf-8"), encoding="utf-8")
            (root / ".springdocker.toml").write_text('[project]\nbuild_tool = "maven"\n', encoding="utf-8")
            dockerfile = root / "Dockerfile.generated"
            dockerfile.write_text("FROM scratch\n", encoding="utf-8")
            (root / "sbom.spdx.json").write_text(json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8")

            def _unexpected_inspect(*_args, **_kwargs):  # type: ignore[no-untyped-def]
                raise AssertionError("inspect_project should not run when config defines build_tool")

            with (
                patch("springdocker.project_detect.inspect_project", side_effect=_unexpected_inspect),
                patch("springdocker.services.verify_service.shutil.which", return_value=None),
                patch(
                    "springdocker.config_audit.run_config_verify_checks",
                    return_value=[("config-drift", "passed", "ok")],
                ),
                patch("springdocker.config_audit.load_config_audit") as load_audit,
            ):
                load_audit.return_value = object()
                outcome = run_verification(
                    VerifyContext(
                        project_root=root,
                        dockerfile_path=dockerfile,
                        image=None,
                        smoke_url=None,
                        check_config_drift=True,
                    )
                )
            drift = next(item for item in outcome.results if item.name == "config-drift")
            self.assertEqual(drift.status, "passed")
            load_audit.assert_called_once()
            self.assertEqual(load_audit.call_args.args[1], "maven")


if __name__ == "__main__":
    unittest.main()
