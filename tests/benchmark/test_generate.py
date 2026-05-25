from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.benchmarks.generate import (
    NativeScenarioDefinition,
    StandardScenarioDefinition,
    default_scenarios,
    generate_benchmark_assets,
)


class GenerateScenarioTests(unittest.TestCase):
    def test_default_scenarios_use_explicit_native_type(self) -> None:
        scenarios = default_scenarios(build_tool="maven", java_version=21)
        native = next(item for item in scenarios if item.id == "07-native-vs-jvm")
        self.assertIsInstance(native, NativeScenarioDefinition)

    def test_standard_scenario_rejects_empty_variants(self) -> None:
        with self.assertRaises(ValueError):
            StandardScenarioDefinition(id="bad", variants=())

    def test_generate_assets_writes_standard_variants_and_keeps_native_folder(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            generate_benchmark_assets(project_root=root, build_tool="maven", java_version=25)
            standard_variant = root / "benchmarks" / "01-multi-stage-build-structure" / "variants" / "specialized-multi-stage" / "Dockerfile"
            self.assertTrue(standard_variant.exists())
            native_dir = root / "benchmarks" / "07-native-vs-jvm" / "variants"
            self.assertTrue(native_dir.exists())

    def test_scenario_variants_match_intended_optimizations(self) -> None:
        scenarios = {scenario.id: scenario for scenario in default_scenarios(build_tool="maven", java_version=25)}
        simple = next(opts for name, opts in scenarios["01-multi-stage-build-structure"].variants if name == "simple-two-stage")
        self.assertFalse(simple.use_jlink)
        self.assertFalse(simple.use_layered_jar)

        with_aot = next(opts for name, opts in scenarios["04-jep483-aot-cache"].variants if name == "with-aot-cache")
        without_aot = next(opts for name, opts in scenarios["04-jep483-aot-cache"].variants if name == "without-aot-cache")
        self.assertTrue(with_aot.enable_jep483_aot_cache)
        self.assertFalse(with_aot.enable_appcds)
        self.assertFalse(without_aot.enable_jep483_aot_cache)

        tuned = next(opts for name, opts in scenarios["05-jvm-container-flags"].variants if name == "tuned-flags")
        defaults = next(opts for name, opts in scenarios["05-jvm-container-flags"].variants if name == "defaults-like")
        self.assertTrue(tuned.tuned_jvm_flags)
        self.assertFalse(defaults.tuned_jvm_flags)
        self.assertEqual(tuned.enable_jep483_aot_cache, defaults.enable_jep483_aot_cache)
        self.assertEqual(tuned.enable_appcds, defaults.enable_appcds)

        with_cds = next(opts for name, opts in scenarios["08-appcds"].variants if name == "with-appcds")
        without_cds = next(opts for name, opts in scenarios["08-appcds"].variants if name == "without-appcds")
        self.assertTrue(with_cds.enable_appcds)
        self.assertFalse(without_cds.enable_appcds)

        base_images = scenarios["06-base-image-choice"]
        self.assertEqual(len(base_images.variants), 5)
        names = {name for name, _ in base_images.variants}
        self.assertEqual(names, {"alpine", "debian-slim", "ubuntu", "distroless", "temurin"})
        debian = next(opts for name, opts in base_images.variants if name == "debian-slim")
        self.assertTrue(debian.use_jlink)
        self.assertEqual(debian.runtime_image, "debian-slim")
        temurin = next(opts for name, opts in base_images.variants if name == "temurin")
        self.assertFalse(temurin.use_jlink)

    def test_custom_base_image_variants_from_config(self) -> None:
        scenarios = default_scenarios(
            build_tool="maven",
            java_version=25,
            base_image_variants=("ubuntu", "temurin"),
        )
        base_images = next(item for item in scenarios if item.id == "06-base-image-choice")
        self.assertEqual(tuple(name for name, _ in base_images.variants), ("ubuntu", "temurin"))


if __name__ == "__main__":
    unittest.main()
