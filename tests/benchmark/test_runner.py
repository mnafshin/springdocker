from __future__ import annotations

import unittest

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.benchmarks.runner import _runtime_flags, parse_runner_args


class RunnerTests(unittest.TestCase):
    def test_runtime_flags_include_isolation_controls(self) -> None:
        self.assertEqual(
            _runtime_flags("0-1", "2g", True),
            [
                "--cpuset-cpus",
                "0-1",
                "--memory",
                "2g",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--tmpfs",
                "/tmp",
            ],
        )

    def test_runtime_flags_empty_when_disabled(self) -> None:
        self.assertEqual(_runtime_flags(None, None, False), [])

    def test_parse_runner_args_recognizes_supported_flags(self) -> None:
        options = parse_runner_args("quick", ["--runs", "2", "--skip-native", "--java-version", "21"])
        self.assertEqual(options.profile, "quick")
        self.assertEqual(options.runs_override, 2)
        self.assertTrue(options.skip_native)
        self.assertEqual(options.java_version, 21)

    def test_parse_runner_args_defaults_java_to_17(self) -> None:
        options = parse_runner_args("quick", ["--skip-native"])
        self.assertEqual(options.java_version, 17)

    def test_parse_runner_args_rejects_removed_native_flags(self) -> None:
        with self.assertRaises(ValueError):
            parse_runner_args("quick", ["--native-duration", "30s"])


if __name__ == "__main__":
    unittest.main()
