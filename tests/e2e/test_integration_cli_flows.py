from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from shutil import copytree
from unittest.mock import patch

from tests.test_support import ROOT, add_src_to_path

add_src_to_path()

from springdocker.cli import main

FIXTURES = ROOT / "tests" / "fixtures"


class _FakeCompleted:
    def __init__(self, returncode: int = 0, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout


class CliIntegrationTests(unittest.TestCase):
    def _workspace_from_fixture(self, name: str) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        td = tempfile.TemporaryDirectory()
        root = Path(td.name) / "project"
        copytree(FIXTURES / name, root)
        return td, root

    def test_doctor_detects_maven_fixture(self) -> None:
        td, project = self._workspace_from_fixture("maven-only")
        self.addCleanup(td.cleanup)
        code = main(["doctor", "--project-root", str(project)])
        self.assertEqual(code, 0)

    def test_doctor_requires_build_tool_for_mixed_markers(self) -> None:
        td, project = self._workspace_from_fixture("mixed-markers")
        self.addCleanup(td.cleanup)
        self.assertEqual(main(["doctor", "--project-root", str(project)]), 2)
        self.assertEqual(main(["doctor", "--project-root", str(project), "--build-tool", "gradle"]), 0)

    def test_generate_and_run_with_internal_paths(self) -> None:
        td, project = self._workspace_from_fixture("gradle-only")
        self.addCleanup(td.cleanup)

        self.assertEqual(
            main(["dockerfile", "generate", "--project-root", str(project), "--output", "Dockerfile.test"]),
            0,
        )
        self.assertTrue((project / "Dockerfile.test").exists())
        self.assertEqual(main(["benchmark", "generate", "--project-root", str(project)]), 0)

        def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
            if args[:3] == ["docker", "image", "inspect"]:
                return _FakeCompleted(stdout="1048576")
            return _FakeCompleted(returncode=0, stdout="")

        with patch("springdocker.benchmarks.runner._wait_readiness", return_value=100), patch(
            "springdocker.benchmarks.runner.subprocess.run", side_effect=fake_run
        ):
            code = main(
                [
                    "benchmark",
                    "run",
                    "--project-root",
                    str(project),
                    "--profile",
                    "quick",
                    "--runner-arg=--runs",
                    "--runner-arg=1",
                    "--runner-arg=--skip-native",
                ]
            )
        self.assertEqual(code, 0)

    def test_dockerfile_generate_reads_must_have_modules_file_from_config(self) -> None:
        cases = (
            (
                "gradle-only",
                'ARG MUSTHAVE_MODULES="jdk.crypto.ec,java.naming"',
            ),
            (
                "maven-only",
                'ARG MUSTHAVE_MODULES="jdk.crypto.ec,java.naming,java.desktop,java.logging,java.management"',
            ),
        )
        for fixture_name, expected_modules_arg in cases:
            with self.subTest(fixture=fixture_name):
                td, project = self._workspace_from_fixture(fixture_name)
                self.addCleanup(td.cleanup)
                build_tool = "gradle" if fixture_name == "gradle-only" else "maven"
                (project / ".springdocker.toml").write_text(
                    "[project]\n"
                    f'build_tool = "{build_tool}"\n\n'
                    "[dockerfile]\n"
                    'output = "Dockerfile.test"\n'
                    "java_version = 25\n"
                    'must_have_modules_file = "must-have.txt"\n',
                    encoding="utf-8",
                )
                (project / "must-have.txt").write_text(
                    "jdk.crypto.ec\n# comment\njava.naming\n",
                    encoding="utf-8",
                )

                code = main(["dockerfile", "generate", "--project-root", str(project)])
                self.assertEqual(code, 0)
                generated = (project / "Dockerfile.test").read_text(encoding="utf-8")
                self.assertIn(expected_modules_arg, generated)

    def test_inspect_outputs_json_for_maven_fixture(self) -> None:
        td, project = self._workspace_from_fixture("maven-only")
        self.addCleanup(td.cleanup)
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(["inspect", "--project-root", str(project), "--format", "json"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["build_tool"], "maven")
        self.assertIn("org.springframework.boot:spring-boot-starter-web", payload["direct_dependencies"])

    def test_explain_generated_dockerfile(self) -> None:
        td, project = self._workspace_from_fixture("maven-only")
        self.addCleanup(td.cleanup)
        self.assertEqual(main(["dockerfile", "generate", "--project-root", str(project), "--output", "Dockerfile.generated"]), 0)
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(["explain", "--project-root", str(project), "Dockerfile.generated", "--format", "json"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["build_tool"], "maven")
        self.assertIn("jlink runtime", [feature["name"] for feature in payload["features"]])

    def test_gradle_kts_fixture_generates_kotlin_descriptor_copy(self) -> None:
        td, project = self._workspace_from_fixture("gradle-kts-only")
        self.addCleanup(td.cleanup)
        self.assertEqual(
            main(["dockerfile", "generate", "--project-root", str(project), "--output", "Dockerfile.generated"]),
            0,
        )
        generated = (project / "Dockerfile.generated").read_text(encoding="utf-8")
        self.assertIn("COPY gradlew build.gradle.kts settings.gradle.kts ./", generated)
        self.assertNotIn("COPY gradlew build.gradle settings.gradle ./", generated)

    def test_golden_maven_and_gradle_paths_cover_core_generation_flows(self) -> None:
        for fixture_name, expected_build_tool in (("maven-only", "maven"), ("gradle-only", "gradle")):
            with self.subTest(fixture=fixture_name):
                td, project = self._workspace_from_fixture(fixture_name)
                self.addCleanup(td.cleanup)

                stdout = StringIO()
                with redirect_stdout(stdout):
                    code = main(["inspect", "--project-root", str(project), "--format", "json"])
                self.assertEqual(code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload["build_tool"], expected_build_tool)

                self.assertEqual(
                    main(["dockerfile", "generate", "--project-root", str(project), "--output", "Dockerfile.generated"]),
                    0,
                )
                generated = (project / "Dockerfile.generated").read_text(encoding="utf-8")
                self.assertIn(f"# Java 17 | build-tool: {expected_build_tool}", generated)
                self.assertIn("FROM --platform=$BUILDPLATFORM", generated)
                self.assertIn("ENTRYPOINT [\"java\"", generated)

                self.assertEqual(main(["benchmark", "generate", "--project-root", str(project)]), 0)
                self.assertTrue(
                    (project / "benchmarks" / "01-custom-jre-jlink" / "variants" / "with-jlink-runtime" / "Dockerfile").exists()
                )
                distroless = (
                    project
                    / "benchmarks"
                    / "03-base-image-choice"
                    / "variants"
                    / "distroless"
                    / "Dockerfile"
                )
                self.assertTrue(distroless.exists())
                self.assertIn("gcr.io/distroless", distroless.read_text(encoding="utf-8"))
                self.assertTrue((project / "benchmarks" / "04-native-benchmark" / "results" / "raw.csv").exists())


if __name__ == "__main__":
    unittest.main()
