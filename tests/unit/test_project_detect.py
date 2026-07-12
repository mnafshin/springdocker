from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.gradle_descriptors import resolve_gradle_descriptor_files
from springdocker.project_detect import (
    analyze_multi_module_layout,
    detect_build_tool,
    has_spring_project_markers,
    has_spring_web_dependency,
    inspect_project_details,
)


class ProjectDetectTests(unittest.TestCase):
    def test_detect_maven(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            self.assertEqual(detect_build_tool(root), "maven")

    def test_detect_gradle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "gradlew").write_text("#!/bin/sh\n", encoding="utf-8")
            self.assertEqual(detect_build_tool(root), "gradle")

    def test_detect_ambiguous_requires_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            (root / "gradlew").write_text("#!/bin/sh\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                detect_build_tool(root)
            self.assertEqual(detect_build_tool(root, "maven"), "maven")

    def test_detect_uses_plugin_detector(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch("springdocker.project_detect.detect_build_tool_from_plugins", return_value="gradle"):
                self.assertEqual(detect_build_tool(root), "gradle")

    def test_spring_markers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app_props = root / "src" / "main" / "resources"
            app_props.mkdir(parents=True)
            (app_props / "application.properties").write_text("spring.application.name=x\n", encoding="utf-8")
            self.assertTrue(has_spring_project_markers(root))

    def test_has_spring_web_dependency_detects_web_starters(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text(
                "<project><dependencies><dependency>"
                "<groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId>"
                "</dependency></dependencies></project>",
                encoding="utf-8",
            )
            self.assertTrue(has_spring_web_dependency(root))

    def test_has_spring_web_dependency_false_for_non_web_starter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text(
                "<project><dependencies><dependency>"
                "<groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter</artifactId>"
                "</dependency></dependencies></project>",
                encoding="utf-8",
            )
            self.assertFalse(has_spring_web_dependency(root))

    def test_has_spring_web_dependency_detects_webflux(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "build.gradle").write_text(
                "dependencies { implementation 'org.springframework.boot:spring-boot-starter-webflux' }\n",
                encoding="utf-8",
            )
            self.assertTrue(has_spring_web_dependency(root))

    def test_inspect_details_maven_namespace_and_reflection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text(
                '<project xmlns="http://maven.apache.org/POM/4.0.0">'
                "<modelVersion>4.0.0</modelVersion>"
                "<parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent</artifactId><version>4.0.1</version></parent>"
                "<properties><java.version>25</java.version></properties>"
                "<dependencies><dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency></dependencies>"
                "</project>",
                encoding="utf-8",
            )
            src = root / "src" / "main" / "java"
            src.mkdir(parents=True)
            (src / "Demo.java").write_text(
                "class Demo { void x() throws Exception { Class.forName(\"x\"); } }\n",
                encoding="utf-8",
            )
            info = inspect_project_details(root)
            self.assertEqual(info.java_version, 25)
            self.assertEqual(info.spring_boot_version, "4.0.1")
            self.assertIn("org.springframework.boot:spring-boot-starter-web", info.direct_dependencies)
            self.assertEqual(info.runtime_compatibility, "compatible")
            self.assertTrue(info.reflection_hits)

    def test_inspect_details_gradle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "build.gradle").write_text(
                "plugins { id 'org.springframework.boot' version '3.3.0' }\n"
                "java { toolchain { languageVersion = JavaLanguageVersion.of(17) } }\n"
                "dependencies { implementation 'org.springframework.boot:spring-boot-starter-web:3.3.0' }\n",
                encoding="utf-8",
            )
            info = inspect_project_details(root)
            self.assertEqual(info.java_version, 17)
            self.assertEqual(info.spring_boot_version, "3.3.0")
            self.assertIn("org.springframework.boot:spring-boot-starter-web", info.direct_dependencies)
            self.assertEqual(info.runtime_compatibility, "compatible")

    def test_maven_reactor_detects_spring_boot_submodule(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text(
                "<project>"
                "<packaging>pom</packaging>"
                "<modules><module>services/api</module></modules>"
                "</project>",
                encoding="utf-8",
            )
            api = root / "services" / "api"
            api.mkdir(parents=True)
            (api / "pom.xml").write_text(
                "<project>"
                "<parent><groupId>org.springframework.boot</groupId>"
                "<artifactId>spring-boot-starter-parent</artifactId><version>3.3.0</version></parent>"
                "<properties><java.version>17</java.version></properties>"
                "<dependencies><dependency><groupId>org.springframework.boot</groupId>"
                "<artifactId>spring-boot-starter-web</artifactId></dependency></dependencies>"
                "</project>",
                encoding="utf-8",
            )
            layout = analyze_multi_module_layout(root, "maven")
            self.assertEqual(layout.kind, "maven-reactor")
            self.assertEqual(layout.modules, ("services/api",))
            self.assertEqual(layout.spring_boot_modules, ("services/api",))
            self.assertTrue(has_spring_project_markers(root, "maven"))

            info = inspect_project_details(root)
            self.assertEqual(info.layout, "maven-reactor")
            self.assertEqual(info.spring_boot_modules, ("services/api",))
            self.assertEqual(info.java_version, 17)
            self.assertEqual(info.spring_boot_version, "3.3.0")
            self.assertTrue(any("services/api" in note for note in info.recommendations))

    def test_gradle_multi_project_detects_spring_boot_subproject(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "gradlew").write_text("#!/bin/sh\n", encoding="utf-8")
            (root / "settings.gradle.kts").write_text(
                'include("app")\n',
                encoding="utf-8",
            )
            app = root / "app"
            app.mkdir()
            (app / "build.gradle.kts").write_text(
                'plugins { id("org.springframework.boot") version "3.3.0" }\n'
                "java { toolchain { languageVersion.set(JavaLanguageVersion.of(17)) } }\n"
                'dependencies { implementation("org.springframework.boot:spring-boot-starter-web:3.3.0") }\n',
                encoding="utf-8",
            )
            layout = analyze_multi_module_layout(root, "gradle")
            self.assertEqual(layout.kind, "gradle-multi-project")
            self.assertEqual(layout.modules, ("app",))
            self.assertEqual(layout.spring_boot_modules, ("app",))
            self.assertTrue(has_spring_project_markers(root, "gradle"))

            info = inspect_project_details(root)
            self.assertEqual(info.layout, "gradle-multi-project")
            self.assertEqual(info.java_version, 17)
            self.assertTrue(any("app" in note for note in info.recommendations))

    def test_resolve_gradle_descriptor_files_kotlin_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "build.gradle.kts").write_text("plugins { id(\"org.springframework.boot\") }\n", encoding="utf-8")
            (root / "settings.gradle.kts").write_text('rootProject.name = "demo"\n', encoding="utf-8")
            self.assertEqual(
                resolve_gradle_descriptor_files(root),
                ("build.gradle.kts", "settings.gradle.kts"),
            )

    def test_resolve_gradle_descriptor_files_includes_version_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "build.gradle.kts").write_text("plugins { id(\"org.springframework.boot\") }\n", encoding="utf-8")
            (root / "settings.gradle.kts").write_text('rootProject.name = "demo"\n', encoding="utf-8")
            catalog = root / "gradle" / "libs.versions.toml"
            catalog.parent.mkdir(parents=True)
            catalog.write_text('[versions]\n', encoding="utf-8")
            self.assertEqual(
                resolve_gradle_descriptor_files(root),
                ("build.gradle.kts", "settings.gradle.kts", "gradle/libs.versions.toml"),
            )

    def test_resolve_gradle_descriptor_files_defaults_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "gradlew").write_text("#!/bin/sh\n", encoding="utf-8")
            self.assertEqual(resolve_gradle_descriptor_files(root), ("build.gradle", "settings.gradle"))


if __name__ == "__main__":
    unittest.main()
