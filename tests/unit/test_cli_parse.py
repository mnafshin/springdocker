from __future__ import annotations

import argparse
import unittest

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.cli import build_parser


class CliParseTests(unittest.TestCase):
    def test_init_parse_profile_and_print(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["init", "--profile", "full", "--print"])
        self.assertEqual(args.command, "init")
        self.assertEqual(args.profile, "full")
        self.assertTrue(args.print_only)

    def test_doctor_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["doctor"])
        self.assertEqual(args.command, "doctor")

    def test_inspect_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["inspect", "--format", "json"])
        self.assertEqual(args.command, "inspect")
        self.assertEqual(args.format, "json")
        self.assertEqual(args.project_root, ".")

    def test_explain_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["explain", "Dockerfile.generated", "--format", "json", "--config-aware"])
        self.assertEqual(args.command, "explain")
        self.assertEqual(args.dockerfile, "Dockerfile.generated")
        self.assertEqual(args.format, "json")
        self.assertTrue(args.config_aware)

    def test_verify_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["verify", "--dockerfile", "Dockerfile.generated", "--image", "demo:latest", "--format", "sarif", "--output", "verify.sarif", "--check-config-drift"]
        )
        self.assertEqual(args.command, "verify")
        self.assertEqual(args.dockerfile, "Dockerfile.generated")
        self.assertEqual(args.image, "demo:latest")
        self.assertEqual(args.format, "sarif")
        self.assertEqual(args.output, "verify.sarif")
        self.assertTrue(args.check_config_drift)
        self.assertFalse(args.trivy_scan_project_root)

    def test_verify_parse_trivy_scan_project_root(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["verify", "--trivy-scan-project-root"])
        self.assertTrue(args.trivy_scan_project_root)

    def test_verify_parse_accepts_plugin_format(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["verify", "--format", "acme-json"])
        self.assertEqual(args.command, "verify")
        self.assertEqual(args.format, "acme-json")

    def test_compare_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["benchmark", "compare", "results/raw.csv", "--baseline-variant", "with-cache"])
        self.assertEqual(args.command, "benchmark")
        self.assertEqual(args.benchmark_command, "compare")
        self.assertEqual(args.raw_csv, "results/raw.csv")
        self.assertEqual(args.baseline_variant, "with-cache")

    def test_dockerfile_generate_parse_internal_flags(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "dockerfile",
                "generate",
                "--output",
                "Dockerfile.prod",
                "--java-version",
                "21",
                "--recipe",
                "spring-aot",
            ]
        )
        self.assertEqual(args.command, "dockerfile")
        self.assertEqual(args.dockerfile_command, "generate")
        self.assertEqual(args.output, "Dockerfile.prod")
        self.assertEqual(args.java_version, 21)
        self.assertEqual(args.recipe, "spring-aot")

    def test_dockerfile_generate_parse_config_flags(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "dockerfile",
                "generate",
                "--runtime-image",
                "alpine",
                "--no-use-jlink",
                "--enable-jep483-aot-cache",
                "--no-include-embedded-sbom",
                "--pin-digests",
                "--jvm-flag=-XX:+UseZGC",
                "--jvm-flag=-XX:MaxRAMPercentage=75",
                "--healthcheck-path",
                "/actuator/health",
            ]
        )
        self.assertEqual(args.runtime_image, "alpine")
        self.assertFalse(args.use_jlink)
        self.assertTrue(args.enable_jep483_aot_cache)
        self.assertFalse(args.include_embedded_sbom)
        self.assertTrue(args.pin_digests)
        self.assertEqual(args.jvm_flag, ["-XX:+UseZGC", "-XX:MaxRAMPercentage=75"])
        self.assertEqual(args.healthcheck_path, "/actuator/health")

    def test_dockerfile_generate_help_groups_config_flags(self) -> None:
        parser = build_parser()
        dockerfile_parser = next(
            action.choices["dockerfile"]
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        gen_parser = next(
            action.choices["generate"]
            for action in dockerfile_parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        help_text = gen_parser.format_help()
        self.assertIn("runtime:\n  Runtime image options", help_text)
        self.assertIn("build:\n  Build and image layout options", help_text)
        self.assertIn("supply chain:\n  Supply chain and reproducibility", help_text)
        self.assertIn("JVM:\n  JVM tuning and caching", help_text)
        self.assertIn("--runtime-image", help_text)
        self.assertIn("--no-include-embedded-sbom", help_text)
        self.assertIn("--jvm-flag", help_text)

    def test_benchmark_run_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["benchmark", "run", "--profile", "full", "--max-workers", "4"])
        self.assertEqual(args.command, "benchmark")
        self.assertEqual(args.benchmark_command, "run")
        self.assertEqual(args.profile, "full")
        self.assertEqual(args.max_workers, 4)

    def test_benchmark_run_parse_reproducibility_flags(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "benchmark",
                "run",
                "--cpuset-cpus",
                "0-1",
                "--memory",
                "2g",
                "--warmup-runs",
                "2",
                "--normalized-runtime",
            ]
        )
        self.assertEqual(args.cpuset_cpus, "0-1")
        self.assertEqual(args.memory, "2g")
        self.assertEqual(args.warmup_runs, 2)
        self.assertTrue(args.normalized_runtime)

    def test_benchmark_analyze_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "benchmark",
            "analyze",
            "results/raw.csv",
            "--format",
            "json",
            "--scenario",
            "02-jep483-aot-cache",
            "--variant",
            "with-aot-cache",
            "--output",
            "out.json",
            "--fail-on-success-rate-below",
            "99.5",
        ])
        self.assertEqual(args.command, "benchmark")
        self.assertEqual(args.benchmark_command, "analyze")
        self.assertEqual(args.format, "json")
        self.assertEqual(args.scenario, "02-jep483-aot-cache")
        self.assertEqual(args.variant, "with-aot-cache")
        self.assertEqual(args.output, "out.json")
        self.assertEqual(args.fail_on_success_rate_below, 99.5)

    def test_benchmark_analyze_regression_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "benchmark",
            "analyze",
            "results/raw.csv",
            "--baseline",
            "baseline.json",
            "--fail-on-regression-above",
            "20",
        ])
        self.assertEqual(args.baseline, "baseline.json")
        self.assertEqual(args.fail_on_regression_above, 20.0)


if __name__ == "__main__":
    unittest.main()
