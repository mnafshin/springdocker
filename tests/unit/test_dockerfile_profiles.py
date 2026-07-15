from __future__ import annotations

import unittest

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.dockerfile import DEFAULT_JVM_FLAGS, DockerfileOptions, build_dockerfile
from springdocker.dockerfile_profiles import (
    PROFILE_NAMES,
    apply_profile,
    apply_profile_for_java,
    default_jvm_flags_for_display,
    profile_description,
)


class DockerfileProfilesTests(unittest.TestCase):
    def test_profile_names_include_custom(self) -> None:
        self.assertIn("production-balanced", PROFILE_NAMES)
        self.assertIn("custom", PROFILE_NAMES)

    def test_production_balanced_matches_distroless_defaults(self) -> None:
        base = DockerfileOptions(build_tool="maven")
        applied = apply_profile(base, "production-balanced")
        self.assertEqual(applied.runtime_image, "distroless")
        self.assertTrue(applied.use_jlink)
        self.assertTrue(applied.include_embedded_sbom)
        self.assertTrue(applied.pin_digests)

    def test_production_balanced_matches_jvm_balanced_default_output(self) -> None:
        baseline = build_dockerfile(DockerfileOptions(build_tool="maven", java_version=25))
        profiled = build_dockerfile(
            apply_profile(DockerfileOptions(build_tool="maven", java_version=25), "production-balanced")
        )
        self.assertEqual(baseline, profiled)

    def test_fast_cold_start_enables_aot(self) -> None:
        applied = apply_profile(DockerfileOptions(build_tool="gradle", java_version=25), "fast-cold-start")
        self.assertTrue(applied.enable_jep483_aot_cache)
        self.assertFalse(applied.enable_appcds)

    def test_fast_cold_start_remaps_to_appcds_on_java_21(self) -> None:
        applied, warning = apply_profile_for_java(
            DockerfileOptions(build_tool="gradle"),
            "fast-cold-start",
            21,
        )
        self.assertFalse(applied.enable_jep483_aot_cache)
        self.assertTrue(applied.enable_appcds)
        self.assertIsNotNone(warning)
        self.assertIn("AppCDS", warning or "")

    def test_fast_cold_start_keeps_aot_on_java_25(self) -> None:
        applied, warning = apply_profile_for_java(
            DockerfileOptions(build_tool="gradle"),
            "fast-cold-start",
            25,
        )
        self.assertTrue(applied.enable_jep483_aot_cache)
        self.assertFalse(applied.enable_appcds)
        self.assertIsNone(warning)

    def test_smallest_image_uses_alpine(self) -> None:
        applied = apply_profile(DockerfileOptions(build_tool="maven"), "smallest-image")
        self.assertEqual(applied.runtime_image, "alpine")

    def test_simplest_disables_jlink(self) -> None:
        applied = apply_profile(DockerfileOptions(build_tool="maven"), "simplest")
        self.assertEqual(applied.runtime_image, "temurin")
        self.assertFalse(applied.use_jlink)
        self.assertFalse(applied.use_layered_jar)

    def test_custom_returns_base_unchanged(self) -> None:
        base = DockerfileOptions(build_tool="gradle", runtime_image="ubuntu")
        self.assertIs(apply_profile(base, "custom"), base)

    def test_unknown_profile_raises(self) -> None:
        with self.assertRaises(ValueError):
            apply_profile(DockerfileOptions(build_tool="maven"), "unknown")

    def test_profile_description_non_empty(self) -> None:
        for name in PROFILE_NAMES:
            self.assertTrue(profile_description(name))

    def test_default_jvm_flags_for_display(self) -> None:
        self.assertEqual(default_jvm_flags_for_display(), DEFAULT_JVM_FLAGS)


if __name__ == "__main__":
    unittest.main()
