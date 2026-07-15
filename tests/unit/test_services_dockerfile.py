from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.dockerfile import NATIVE_AOT_SCAFFOLD_WARNING
from springdocker.services.dockerfile_service import generate_dockerfile, parse_must_have_modules


class DockerfileServiceTests(unittest.TestCase):
    def test_parse_must_have_modules_deduplicates_and_strips_comments(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            modules_file = root / "modules.txt"
            modules_file.write_text(
                "java.sql, java.naming\n"
                "java.naming # duplicate\n"
                "java.management\n",
                encoding="utf-8",
            )
            parsed = parse_must_have_modules(root, "modules.txt")
            self.assertEqual(parsed, ("java.sql", "java.naming", "java.management"))

    def test_parse_must_have_modules_rejects_invalid_name(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            modules_file = root / "modules.txt"
            modules_file.write_text("java.base\nbad module\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_must_have_modules(root, "modules.txt")

    def test_generate_dockerfile_creates_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            generated = generate_dockerfile(
                project_root=root,
                output_path="nested/Dockerfile.generated",
                build_tool="maven",
                java_version=21,
                must_have_modules_file=None,
            )
            destination = generated.path
            self.assertTrue(destination.exists())
            self.assertIn("FROM --platform=$BUILDPLATFORM eclipse-temurin:21-jdk@", destination.read_text("utf-8"))
            self.assertTrue((root / ".dockerignore").exists())

    def test_generate_dockerfile_omits_healthcheck_on_distroless_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text(
                "<project><dependencies><dependency><groupId>org.springframework.boot</groupId>"
                "<artifactId>spring-boot-starter-actuator</artifactId></dependency></dependencies></project>",
                encoding="utf-8",
            )
            generated = generate_dockerfile(
                project_root=root,
                output_path="Dockerfile.generated",
                build_tool="maven",
                java_version=21,
                must_have_modules_file=None,
            )
            rendered = generated.path.read_text("utf-8")
            self.assertIn("gcr.io/distroless/base-debian", rendered)
            self.assertNotIn("HEALTHCHECK --interval=15s", rendered)

    def test_generate_dockerfile_injects_jlink_baseline_for_web_project(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text(
                "<project><dependencies><dependency><groupId>org.springframework.boot</groupId>"
                "<artifactId>spring-boot-starter-web</artifactId></dependency></dependencies></project>",
                encoding="utf-8",
            )
            generated = generate_dockerfile(
                project_root=root,
                output_path="Dockerfile.generated",
                build_tool="maven",
                java_version=21,
                must_have_modules_file=None,
            )
            rendered = generated.path.read_text("utf-8")
            self.assertIn('ARG MUSTHAVE_MODULES="java.desktop,java.logging,java.naming,java.management"', rendered)

    def test_generate_dockerfile_omits_jlink_baseline_for_non_web_project(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text(
                "<project><dependencies><dependency><groupId>org.springframework.boot</groupId>"
                "<artifactId>spring-boot-starter</artifactId></dependency></dependencies></project>",
                encoding="utf-8",
            )
            generated = generate_dockerfile(
                project_root=root,
                output_path="Dockerfile.generated",
                build_tool="maven",
                java_version=21,
                must_have_modules_file=None,
            )
            rendered = generated.path.read_text("utf-8")
            self.assertNotIn("java.desktop", rendered)
            self.assertIn('ARG MUSTHAVE_MODULES=""', rendered)

    def test_generate_dockerfile_native_aot_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            generated = generate_dockerfile(
                project_root=root,
                output_path="Dockerfile.native",
                build_tool="gradle",
                java_version=21,
                must_have_modules_file=None,
                recipe="native-aot",
            )
            rendered = generated.path.read_text("utf-8")
            self.assertIn("native-image-community:21", rendered)
            self.assertIn("nativeCompile -x test", rendered)
            self.assertIn('ENTRYPOINT ["/app/app"]', rendered)
            self.assertIn("scaffold: experimental native-image Dockerfile", rendered)
            self.assertIn(NATIVE_AOT_SCAFFOLD_WARNING, generated.plugin_warnings)

    def test_generate_dockerfile_uses_recipe_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch(
                "springdocker.services.dockerfile_service.render_recipe_from_plugins",
                return_value=type("R", (), {"rendered": "FROM scratch\n", "handled": True, "warnings": ()})(),
            ):
                generated = generate_dockerfile(
                    project_root=root,
                    output_path="Dockerfile.plugin",
                    build_tool="maven",
                    java_version=21,
                    must_have_modules_file=None,
                    recipe="acme",
                )
            self.assertEqual(generated.path.read_text("utf-8"), "FROM scratch\n")

    def test_generate_dockerfile_uses_kotlin_gradle_descriptors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "build.gradle.kts").write_text(
                'plugins { id("org.springframework.boot") version "3.3.0" }\n',
                encoding="utf-8",
            )
            (root / "settings.gradle.kts").write_text('rootProject.name = "demo"\n', encoding="utf-8")
            generated = generate_dockerfile(
                project_root=root,
                output_path="Dockerfile.generated",
                build_tool="gradle",
                java_version=21,
                must_have_modules_file=None,
            )
            rendered = generated.path.read_text("utf-8")
            self.assertIn("COPY gradlew build.gradle.kts settings.gradle.kts ./", rendered)
            self.assertNotIn("COPY gradlew build.gradle settings.gradle ./", rendered)


if __name__ == "__main__":
    unittest.main()
