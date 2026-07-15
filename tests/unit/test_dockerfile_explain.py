from __future__ import annotations

import unittest

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.dockerfile import DockerfileOptions, build_dockerfile
from springdocker.dockerfile_explain import explain_dockerfile_text


class DockerfileExplainTests(unittest.TestCase):
    def test_explain_generated_dockerfile_detects_core_features(self) -> None:
        text = build_dockerfile(DockerfileOptions(build_tool="maven", java_version=25))
        payload = explain_dockerfile_text(text)

        self.assertEqual(payload["build_tool"], "maven")
        self.assertEqual(payload["java_version"], 25)
        self.assertGreaterEqual(payload["stage_count"], 2)
        feature_names = [feature["name"] for feature in payload["features"]]
        self.assertIn("jlink runtime", feature_names)
        self.assertIn("jlink baseline modules", feature_names)
        self.assertEqual(
            payload["jlink_modules"]["baseline"],
            ["java.desktop", "java.logging", "java.naming", "java.management"],
        )

    def test_explain_distinguishes_baseline_and_curated_modules(self) -> None:
        text = build_dockerfile(
            DockerfileOptions(
                build_tool="maven",
                java_version=25,
                must_have_modules=("jdk.crypto.ec",),
            )
        )
        payload = explain_dockerfile_text(text)

        self.assertEqual(payload["jlink_modules"]["curated"], ["jdk.crypto.ec"])
        feature_names = [feature["name"] for feature in payload["features"]]
        self.assertIn("must-have modules", feature_names)

    def test_explain_manual_dockerfile_uses_fallback_heuristics(self) -> None:
        text = "FROM eclipse-temurin:21-jdk\nRUN ./mvnw package\n"
        payload = explain_dockerfile_text(text)

        self.assertEqual(payload["build_tool"], "maven")
        self.assertEqual(payload["java_version"], 21)
        self.assertEqual(payload["stage_count"], 1)
        self.assertIn("targets Java 21", payload["summary"])
        self.assertNotIn("jlink runtime", [feature["name"] for feature in payload["features"]])

    def test_explain_distroless_runtime_feature(self) -> None:
        text = build_dockerfile(
            DockerfileOptions(build_tool="maven", java_version=21, runtime_image="distroless", use_jlink=False)
        )
        payload = explain_dockerfile_text(text)
        feature_names = [feature["name"] for feature in payload["features"]]
        self.assertIn("distroless runtime", feature_names)
        self.assertIn("non-root runtime", feature_names)

    def test_explain_includes_static_analysis_notes(self) -> None:
        payload = explain_dockerfile_text("FROM scratch\n")
        notes = payload["notes"]
        self.assertIn("Advisory static analysis only", notes[0])
        self.assertIn("springdocker verify", notes[-1])


if __name__ == "__main__":
    unittest.main()
