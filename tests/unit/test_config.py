from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.config import (
    load_config,
    render_default_config,
    resolve_benchmark_generate_config,
    resolve_benchmark_run_config,
    resolve_dockerfile_generate_config,
    resolve_doctor_config,
)
from springdocker.dockerfile import JLINK_BASELINE_MODULES


class ConfigTests(unittest.TestCase):
    def test_load_missing_config_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cfg = load_config(Path(td) / ".springdocker.toml")
            self.assertEqual(cfg, {})

    def test_resolve_benchmark_config_from_file(self) -> None:
        loaded = {
            "project": {"build_tool": "maven"},
            "benchmark": {
                "run": {
                    "profile": "full",
                    "runner_args": ["--skip-native"],
                    "cpuset_cpus": "0-1",
                    "memory_limit": "2g",
                    "warmup_runs": 2,
                    "max_workers": 2,
                    "normalized_runtime": True,
                    "legacy_scripts": True,
                }
            },
        }
        resolved = resolve_benchmark_run_config(None, None, None, None, None, None, None, None, None, loaded)
        self.assertEqual(resolved.build_tool, "maven")
        self.assertEqual(resolved.profile, "full")
        self.assertEqual(resolved.runner_args, ["--skip-native"])
        self.assertEqual(resolved.cpuset_cpus, "0-1")
        self.assertEqual(resolved.memory_limit, "2g")
        self.assertEqual(resolved.warmup_runs, 2)
        self.assertEqual(resolved.max_workers, 2)
        self.assertTrue(resolved.normalized_runtime)
        self.assertTrue(resolved.use_legacy_scripts)

    def test_cli_overrides_config(self) -> None:
        loaded = {
            "project": {"build_tool": "maven"},
            "benchmark": {
                "run": {
                    "profile": "full",
                    "runner_args": ["--skip-native"],
                    "cpuset_cpus": "0-1",
                    "memory_limit": "2g",
                    "warmup_runs": 1,
                    "normalized_runtime": False,
                }
            },
        }
        resolved = resolve_benchmark_run_config("gradle", "quick", ["--runs", "2"], "2-3", "1g", 0, 3, True, False, loaded)
        self.assertEqual(resolved.build_tool, "gradle")
        self.assertEqual(resolved.profile, "quick")
        self.assertEqual(resolved.runner_args, ["--runs", "2"])
        self.assertEqual(resolved.cpuset_cpus, "2-3")
        self.assertEqual(resolved.memory_limit, "1g")
        self.assertEqual(resolved.warmup_runs, 0)
        self.assertEqual(resolved.max_workers, 3)
        self.assertTrue(resolved.normalized_runtime)
        self.assertFalse(resolved.use_legacy_scripts)

    def test_resolve_other_command_configs(self) -> None:
        loaded = {
            "project": {"build_tool": "gradle"},
            "doctor": {"build_tool": "maven"},
            "dockerfile": {
                "output": "Dockerfile.ci",
                "java_version": 21,
                "recipe": "spring-aot",
                "must_have_modules_file": "must-have.txt",
                "legacy_scripts": True,
                "wizard_args": ["--profile", "balanced"],
            },
            "benchmark": {
                "generate": {"java_version": 21, "legacy_scripts": True},
            },
        }
        doctor = resolve_doctor_config(None, loaded)
        dockerfile = resolve_dockerfile_generate_config(None, None, None, None, None, None, loaded)
        bench_generate = resolve_benchmark_generate_config(None, None, None, loaded)
        self.assertEqual(doctor.build_tool, "maven")
        self.assertEqual(dockerfile.build_tool, "gradle")
        self.assertEqual(dockerfile.output, "Dockerfile.ci")
        self.assertEqual(dockerfile.java_version, 21)
        self.assertEqual(dockerfile.recipe, "spring-aot")
        self.assertEqual(dockerfile.must_have_modules_file, "must-have.txt")
        self.assertEqual(dockerfile.jlink_baseline_modules, JLINK_BASELINE_MODULES)
        self.assertTrue(dockerfile.use_legacy_scripts)
        self.assertEqual(bench_generate.java_version, 21)
        self.assertTrue(bench_generate.use_legacy_scripts)
        self.assertEqual(
            bench_generate.base_image_variants,
            ("alpine", "debian-slim", "ubuntu", "distroless"),
        )

    def test_resolve_jlink_baseline_modules_from_config(self) -> None:
        loaded = {
            "dockerfile": {
                "jlink_baseline_modules": ["java.logging"],
            }
        }
        resolved = resolve_dockerfile_generate_config(None, None, None, None, None, None, loaded)
        self.assertEqual(resolved.jlink_baseline_modules, ("java.logging",))

        empty_loaded = {"dockerfile": {"jlink_baseline_modules": []}}
        empty_resolved = resolve_dockerfile_generate_config(None, None, None, None, None, None, empty_loaded)
        self.assertEqual(empty_resolved.jlink_baseline_modules, ())

    def test_render_default_config_documents_jlink_baseline_modules(self) -> None:
        text = render_default_config("maven")
        self.assertIn("jlink_baseline_modules", text)
        self.assertIn("java.desktop", text)
        self.assertIn("Default generator runtime: distroless", text)
        self.assertIn("HEALTHCHECK is omitted", text)

    def test_resolve_base_image_variants_from_config(self) -> None:
        loaded = {
            "benchmark": {
                "generate": {
                    "base_image_choice": {
                        "variants": ["debian-slim", "distroless"],
                    }
                }
            }
        }
        resolved = resolve_benchmark_generate_config(None, None, None, loaded)
        self.assertEqual(resolved.base_image_variants, ("debian-slim", "distroless"))

    def test_strict_unknown_key_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / ".springdocker.toml"
            cfg.write_text("[project]\nbuild_tool='maven'\n[unknown]\na=1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(cfg, strict=True)


if __name__ == "__main__":
    unittest.main()
