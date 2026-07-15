from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.commands import (
    cmd_benchmark_generate,
    cmd_benchmark_run,
    cmd_dockerfile_generate,
    cmd_explain,
    cmd_verify,
)
from springdocker.config import sample_dockerfile_config
from springdocker.dockerfile import DockerfileOptions, build_dockerfile


class _FakeCompleted:
    def __init__(self, returncode: int = 0, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout


class InternalFlowTests(unittest.TestCase):
    def test_dockerfile_generate_without_legacy_script(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            code = cmd_dockerfile_generate(
                project_root=root,
                config=sample_dockerfile_config(output="Dockerfile.generated", java_version=21),
            )
            self.assertEqual(code, 0)
            generated = (root / "Dockerfile.generated").read_text(encoding="utf-8")
            self.assertTrue((root / "Dockerfile.generated").exists())
            self.assertIn("VOLUME /tmp", generated)
            self.assertIn("ARG TARGETPLATFORM", generated)
            self.assertIn("--platform=$BUILDPLATFORM", generated)
            self.assertIn("/usr/share/sbom/spdx.json", generated)
            self.assertIn("SOURCE_DATE_EPOCH", generated)

    def test_benchmark_generate_without_legacy_script(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            code = cmd_benchmark_generate(
                project_root=root,
                build_tool=None,
                java_version=25,
                use_legacy_scripts=False,
            )
            self.assertEqual(code, 0)
            self.assertTrue((root / "benchmarks" / "01-custom-jre-jlink" / "variants").exists())
            distroless = root / "benchmarks" / "03-base-image-choice" / "variants" / "distroless" / "Dockerfile"
            self.assertTrue(distroless.exists())
            self.assertIn("gcr.io/distroless", distroless.read_text(encoding="utf-8"))

    def test_benchmark_run_without_legacy_script(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            cmd_benchmark_generate(project_root=root, build_tool=None, java_version=25, use_legacy_scripts=False)

            def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
                if args[:3] == ["docker", "image", "inspect"]:
                    return _FakeCompleted(stdout="1048576")
                return _FakeCompleted(returncode=0, stdout="")

            with patch("springdocker.benchmarks.runner._wait_readiness", return_value=100), patch(
                "springdocker.benchmarks.runner.subprocess.run", side_effect=fake_run
            ):
                stdout = StringIO()
                with redirect_stdout(stdout):
                    code = cmd_benchmark_run(
                        project_root=root,
                        build_tool=None,
                        profile="quick",
                        extra_args=["--runs", "1", "--skip-native"],
                        cpuset_cpus=None,
                        memory_limit=None,
                        warmup_runs=0,
                        normalized_runtime=False,
                        use_legacy_scripts=False,
                    )
            self.assertEqual(code, 0)
            raw_csv = root / "benchmarks" / "01-custom-jre-jlink" / "results" / "raw.csv"
            self.assertTrue(raw_csv.exists())
            self.assertIn("01-custom-jre-jlink", raw_csv.read_text(encoding="utf-8"))
            self.assertIn("=== Scenario: 01-custom-jre-jlink", stdout.getvalue())
            self.assertIn("run 1:", stdout.getvalue())
            self.assertIn("Skipping native scaffold scenario: 04-native-benchmark", stdout.getvalue())

    def test_benchmark_generate_warns_when_legacy_scripts_requested(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            script_dir = root / "benchmarks"
            script_dir.mkdir()
            (script_dir / "setup_benchmark_folders.py").write_text("# legacy\n", encoding="utf-8")
            stderr = StringIO()
            with patch("springdocker.commands.run_checked", return_value=0), redirect_stderr(stderr):
                code = cmd_benchmark_generate(
                    project_root=root,
                    build_tool=None,
                    java_version=25,
                    use_legacy_scripts=True,
                )
            self.assertEqual(code, 0)
            self.assertIn("deprecated", stderr.getvalue())
            self.assertIn("v2.0.0", stderr.getvalue())

    def test_benchmark_generate_warns_when_legacy_scripts_env_set(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            script_dir = root / "benchmarks"
            script_dir.mkdir()
            (script_dir / "setup_benchmark_folders.py").write_text("# legacy\n", encoding="utf-8")
            stderr = StringIO()
            with patch.dict(os.environ, {"SPRINGDOCKER_LEGACY_SCRIPTS": "1"}, clear=False), patch(
                "springdocker.commands.run_checked", return_value=0
            ), redirect_stderr(stderr):
                code = cmd_benchmark_generate(
                    project_root=root,
                    build_tool=None,
                    java_version=25,
                    use_legacy_scripts=False,
                )
            self.assertEqual(code, 0)
            self.assertIn("SPRINGDOCKER_LEGACY_SCRIPTS", stderr.getvalue())

    def test_dockerfile_generate_round_trips_to_explain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            code = cmd_dockerfile_generate(
                project_root=root,
                config=sample_dockerfile_config(output="Dockerfile.generated", java_version=25),
            )
            self.assertEqual(code, 0)
            stdout = StringIO()
            with redirect_stdout(stdout):
                explain_code = cmd_explain(root, "Dockerfile.generated", "table")
            self.assertEqual(explain_code, 0)
            self.assertIn("jlink runtime", stdout.getvalue())

    def test_distroless_dockerfile_generation(self) -> None:
        dockerfile = build_dockerfile(
            DockerfileOptions(
                build_tool="maven",
                java_version=25,
                runtime_image="distroless",
                use_jlink=False,
            )
        )
        self.assertIn("gcr.io/distroless/java25-debian13:nonroot", dockerfile)
        self.assertNotIn("RUN groupadd", dockerfile)
        self.assertNotIn("RUN install -d -m 755 /app", dockerfile)

    def test_verify_writes_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dockerfile = root / "Dockerfile.generated"
            dockerfile.write_text("FROM scratch\n", encoding="utf-8")
            (root / "sbom.spdx.json").write_text('{"spdxVersion":"SPDX-2.3"}', encoding="utf-8")
            report = root / "verify.json"
            with patch("springdocker.services.verify_service.shutil.which", return_value=None):
                code = cmd_verify(
                    project_root=root,
                    dockerfile_path="Dockerfile.generated",
                    image=None,
                    smoke_url=None,
                    output_format="json",
                    output_path="verify.json",
                )
            self.assertEqual(code, 0)
            self.assertTrue(report.exists())
            self.assertIn('"overall": "passed"', report.read_text(encoding="utf-8"))

    def test_verify_rejects_unknown_format(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dockerfile = root / "Dockerfile.generated"
            dockerfile.write_text("FROM scratch\n", encoding="utf-8")
            (root / "sbom.spdx.json").write_text('{"spdxVersion":"SPDX-2.3"}', encoding="utf-8")
            code = cmd_verify(
                project_root=root,
                dockerfile_path="Dockerfile.generated",
                image=None,
                smoke_url=None,
                output_format="acme-json",
                output_path=None,
            )
            self.assertEqual(code, 2)

    def test_benchmark_run_rejects_reproducibility_controls_with_legacy_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            stderr = StringIO()
            with redirect_stderr(stderr):
                code = cmd_benchmark_run(
                    project_root=root,
                    build_tool=None,
                    profile="quick",
                    extra_args=[],
                    cpuset_cpus="0-1",
                    memory_limit=None,
                    warmup_runs=0,
                    normalized_runtime=False,
                    use_legacy_scripts=True,
                )
            self.assertEqual(code, 2)
            self.assertIn("internal benchmark runner", stderr.getvalue())

    def test_benchmark_generate_requires_optional_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            stderr = StringIO()
            with patch(
                "springdocker.commands.benchmark_service.require_benchmark_dependencies",
                side_effect=ValueError("benchmark subsystem is optional"),
            ), redirect_stderr(stderr):
                code = cmd_benchmark_generate(
                    project_root=root,
                    build_tool=None,
                    java_version=25,
                    use_legacy_scripts=False,
                )
            self.assertEqual(code, 2)
            self.assertIn("benchmark subsystem is optional", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
