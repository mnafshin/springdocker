from __future__ import annotations

import unittest

from tests.test_support import ROOT, add_src_to_path

add_src_to_path()

from springdocker.dockerfile import DockerfileOptions, build_dockerfile

SNAPSHOT_DIR = ROOT / "tests" / "snapshots" / "dockerfile"


class DockerfileSnapshotTests(unittest.TestCase):
    def assert_snapshot(self, name: str, options: DockerfileOptions) -> None:
        expected = (SNAPSHOT_DIR / f"{name}.Dockerfile").read_text(encoding="utf-8")
        actual = build_dockerfile(options)
        self.assertEqual(actual, expected)

    def test_gradle_kts_minimal_snapshot(self) -> None:
        self.assert_snapshot(
            "gradle-kts-minimal",
            DockerfileOptions(
                build_tool="gradle",
                java_version=21,
                gradle_descriptor_files=("build.gradle.kts", "settings.gradle.kts"),
                use_buildkit_cache=False,
                use_jlink=False,
                non_root=False,
                tuned_jvm_flags=False,
                platform_aware=False,
            ),
        )

    def test_maven_default_snapshot(self) -> None:
        self.assert_snapshot("maven-default", DockerfileOptions(build_tool="maven", java_version=25))

    def test_gradle_minimal_snapshot(self) -> None:
        self.assert_snapshot(
            "gradle-minimal",
            DockerfileOptions(
                build_tool="gradle",
                java_version=21,
                use_buildkit_cache=False,
                use_jlink=False,
                non_root=False,
                tuned_jvm_flags=False,
                platform_aware=False,
            ),
        )

    def test_maven_must_have_modules_snapshot(self) -> None:
        self.assert_snapshot(
            "maven-must-have",
            DockerfileOptions(
                build_tool="maven",
                java_version=25,
                must_have_modules=("jakarta.persistence", "org.slf4j"),
            ),
        )

    def test_distroless_snapshot(self) -> None:
        self.assert_snapshot(
            "distroless",
            DockerfileOptions(build_tool="maven", java_version=21, runtime_image="distroless", use_jlink=False),
        )


if __name__ == "__main__":
    unittest.main()
