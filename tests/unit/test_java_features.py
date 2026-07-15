from __future__ import annotations

import unittest

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.dockerfile import DockerfileOptions
from springdocker.java_features import (
    JEP483_MIN_JAVA,
    MIN_JAVA_VERSION,
    FeatureAvailability,
    features_for,
    validate_dockerfile_options,
)


class JavaFeaturesTests(unittest.TestCase):
    def test_constants(self) -> None:
        self.assertEqual(MIN_JAVA_VERSION, 17)
        self.assertEqual(JEP483_MIN_JAVA, 24)

    def test_features_for_java_17(self) -> None:
        available = features_for(17)
        self.assertIsInstance(available, FeatureAvailability)
        self.assertTrue(available.jlink)
        self.assertTrue(available.appcds)
        self.assertTrue(available.layered_jar)
        self.assertTrue(available.tuned_jvm_flags)
        self.assertFalse(available.jep483_aot_cache)
        self.assertTrue(available.native_aot_recipe)

    def test_features_for_java_24(self) -> None:
        available = features_for(24)
        self.assertTrue(available.jep483_aot_cache)

    def test_features_for_rejects_below_floor(self) -> None:
        with self.assertRaises(ValueError):
            features_for(16)

    def test_validate_rejects_aot_on_java_17(self) -> None:
        options = DockerfileOptions(
            build_tool="maven",
            java_version=17,
            enable_jep483_aot_cache=True,
            enable_appcds=False,
        )
        with self.assertRaises(ValueError) as ctx:
            validate_dockerfile_options(options)
        self.assertIn("24", str(ctx.exception))

    def test_validate_accepts_appcds_on_java_17(self) -> None:
        options = DockerfileOptions(
            build_tool="maven",
            java_version=17,
            enable_appcds=True,
            enable_jep483_aot_cache=False,
        )
        validate_dockerfile_options(options)

    def test_validate_accepts_aot_on_java_24(self) -> None:
        options = DockerfileOptions(
            build_tool="maven",
            java_version=24,
            enable_jep483_aot_cache=True,
            enable_appcds=False,
        )
        validate_dockerfile_options(options)

    def test_validate_accepts_aot_on_java_25(self) -> None:
        options = DockerfileOptions(
            build_tool="maven",
            java_version=25,
            enable_jep483_aot_cache=True,
            enable_appcds=False,
        )
        validate_dockerfile_options(options)

    def test_validate_rejects_aot_without_jlink(self) -> None:
        options = DockerfileOptions(
            build_tool="maven",
            java_version=25,
            use_jlink=False,
            enable_jep483_aot_cache=True,
            enable_appcds=False,
        )
        with self.assertRaises(ValueError) as ctx:
            validate_dockerfile_options(options)
        self.assertIn("jlink", str(ctx.exception).lower())

    def test_validate_rejects_appcds_and_aot_together(self) -> None:
        options = DockerfileOptions(
            build_tool="maven",
            java_version=25,
            enable_jep483_aot_cache=True,
            enable_appcds=True,
        )
        with self.assertRaises(ValueError):
            validate_dockerfile_options(options)


if __name__ == "__main__":
    unittest.main()
