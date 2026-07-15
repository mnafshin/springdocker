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
from springdocker.config import sample_dockerfile_config


class GenerateScenarioTests(unittest.TestCase):
    def test_default_scenarios_use_explicit_native_type(self) -> None:
        scenarios = default_scenarios(build_tool="maven", java_version=21)
        native = next(item for item in scenarios if item.id == "04-native-benchmark")
        self.assertIsInstance(native, NativeScenarioDefinition)

    def test_standard_scenario_rejects_empty_variants(self) -> None:
        with self.assertRaises(ValueError):
            StandardScenarioDefinition(id="bad", variants=())

    def test_generate_assets_writes_standard_variants_and_keeps_native_folder(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            generate_benchmark_assets(project_root=root, build_tool="maven", java_version=25)
            standard_variant = (
                root / "benchmarks" / "01-custom-jre-jlink" / "variants" / "with-jlink-runtime" / "Dockerfile"
            )
            self.assertTrue(standard_variant.exists())
            native_dockerfile = root / "benchmarks" / "04-native-benchmark" / "Dockerfile"
            self.assertTrue(native_dockerfile.exists())
            self.assertIn("scaffold: experimental native-image Dockerfile", native_dockerfile.read_text("utf-8"))
            native_readme = root / "benchmarks" / "04-native-benchmark" / "README.md"
            self.assertTrue(native_readme.exists())
            self.assertIn("experimental scaffold output only", native_readme.read_text("utf-8"))
            native_variants_dir = root / "benchmarks" / "04-native-benchmark" / "variants"
            self.assertFalse(native_variants_dir.exists())
            recipes = root / "example-dockerfiles" / "recipes"
            jvm_balanced = recipes / "jvm-balanced.Dockerfile"
            spring_aot = recipes / "spring-aot.Dockerfile"
            native_aot = recipes / "native-aot.Dockerfile"
            self.assertTrue(jvm_balanced.exists())
            self.assertTrue(spring_aot.exists())
            self.assertTrue(native_aot.exists())
            self.assertIn("https://github.com/mnafshin/springdocker", jvm_balanced.read_text("utf-8"))
            self.assertIn("gcr.io/distroless/base-debian", jvm_balanced.read_text("utf-8"))
            self.assertIn("process-aot", spring_aot.read_text("utf-8"))
            self.assertIn("native:compile", native_aot.read_text("utf-8"))
            self.assertFalse((root / "example-dockerfiles" / "01-custom-jre-jlink").exists())

    def test_recipe_examples_use_dockerfile_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "musthave_modules.txt").write_text("java.base\n", encoding="utf-8")
            dockerfile_config = sample_dockerfile_config(
                must_have_modules_file="musthave_modules.txt",
                enable_appcds=True,
                enable_jep483_aot_cache=False,
            )
            generate_benchmark_assets(
                project_root=root,
                build_tool="maven",
                java_version=25,
                dockerfile_config=dockerfile_config,
            )
            jvm_balanced = (root / "example-dockerfiles" / "recipes" / "jvm-balanced.Dockerfile").read_text("utf-8")
            self.assertIn("ArchiveClassesAtExit", jvm_balanced)
            self.assertIn("SharedArchiveFile", jvm_balanced)

    def test_scenario_variants_match_intended_optimizations(self) -> None:
        scenarios = {scenario.id: scenario for scenario in default_scenarios(build_tool="maven", java_version=25)}
        self.assertEqual(
            set(scenarios),
            {
                "01-custom-jre-jlink",
                "02-jep483-aot-cache",
                "03-base-image-choice",
                "04-native-benchmark",
                "05-appcds",
            },
        )

        with_jlink = next(opts for name, opts in scenarios["01-custom-jre-jlink"].variants if name == "with-jlink-runtime")
        without_jlink = next(
            opts for name, opts in scenarios["01-custom-jre-jlink"].variants if name == "without-jlink-runtime"
        )
        temurin_jre = next(opts for name, opts in scenarios["01-custom-jre-jlink"].variants if name == "temurin-jre-image")
        self.assertTrue(with_jlink.use_jlink)
        self.assertEqual(with_jlink.runtime_image, "debian-slim")
        self.assertFalse(without_jlink.use_jlink)
        self.assertEqual(without_jlink.runtime_image, "debian-slim")
        self.assertFalse(temurin_jre.use_jlink)
        self.assertEqual(temurin_jre.runtime_image, "temurin")

        with_aot = next(opts for name, opts in scenarios["02-jep483-aot-cache"].variants if name == "with-aot-cache")
        without_aot = next(opts for name, opts in scenarios["02-jep483-aot-cache"].variants if name == "without-aot-cache")
        self.assertTrue(with_aot.enable_jep483_aot_cache)
        self.assertFalse(with_aot.enable_appcds)
        self.assertFalse(without_aot.enable_jep483_aot_cache)

        with_cds = next(opts for name, opts in scenarios["05-appcds"].variants if name == "with-appcds")
        without_cds = next(opts for name, opts in scenarios["05-appcds"].variants if name == "without-appcds")
        self.assertTrue(with_cds.enable_appcds)
        self.assertFalse(without_cds.enable_appcds)

        base_images = scenarios["03-base-image-choice"]
        self.assertEqual(len(base_images.variants), 4)
        names = {name for name, _ in base_images.variants}
        self.assertEqual(names, {"alpine", "debian-slim", "ubuntu", "distroless"})
        debian = next(opts for name, opts in base_images.variants if name == "debian-slim")
        self.assertTrue(debian.use_jlink)
        self.assertEqual(debian.runtime_image, "debian-slim")
        distroless = next(opts for name, opts in base_images.variants if name == "distroless")
        self.assertTrue(distroless.use_jlink)

    def test_jep483_scenario_omitted_for_java_21(self) -> None:
        scenarios = {scenario.id: scenario for scenario in default_scenarios(build_tool="maven", java_version=21)}
        self.assertNotIn("02-jep483-aot-cache", scenarios)
        self.assertIn("05-appcds", scenarios)

    def test_jep483_scenario_present_for_java_25(self) -> None:
        scenarios = {scenario.id for scenario in default_scenarios(build_tool="maven", java_version=25)}
        self.assertIn("02-jep483-aot-cache", scenarios)

    def test_generate_assets_omits_jep483_dir_for_java_21(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            generate_benchmark_assets(project_root=root, build_tool="maven", java_version=21)
            self.assertFalse((root / "benchmarks" / "02-jep483-aot-cache").exists())
            self.assertTrue((root / "benchmarks" / "05-appcds").exists())

    def test_custom_base_image_variants_from_config(self) -> None:
        scenarios = default_scenarios(
            build_tool="maven",
            java_version=25,
            base_image_variants=("ubuntu", "temurin"),
        )
        base_images = next(item for item in scenarios if item.id == "03-base-image-choice")
        self.assertEqual(tuple(name for name, _ in base_images.variants), ("ubuntu", "temurin"))


if __name__ == "__main__":
    unittest.main()
