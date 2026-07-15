from __future__ import annotations

import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.test_support import ROOT, add_src_to_path

add_src_to_path()

from springdocker.cli import build_parser, main
from springdocker.commands import cmd_configure
from springdocker.config import load_config, resolve_dockerfile_generate_config
from springdocker.configure_wizard import (
    _edit_jvm_flags,
    _startup_optimization_choice,
    ask_bool,
    ask_choice,
    run_configure_wizard,
)


class ConfigureWizardTests(unittest.TestCase):
    def test_run_configure_wizard_writes_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project></project>", encoding="utf-8")
            config_path = root / ".springdocker.toml"
            with (
                patch("springdocker.configure_wizard.ask_choice", return_value="production-balanced"),
                patch("springdocker.configure_wizard.ask_bool", return_value=True),
            ):
                run_configure_wizard(root, config_path)
            self.assertTrue(config_path.exists())
            text = config_path.read_text("utf-8")
            self.assertIn("[dockerfile]", text)
            self.assertIn('profile = "production-balanced"', text)
            self.assertIn('runtime_image = "distroless"', text)

    def test_cmd_configure_requires_force_when_config_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project></project>", encoding="utf-8")
            config_path = root / ".springdocker.toml"
            config_path.write_text("[project]\nbuild_tool = \"maven\"\n", encoding="utf-8")
            stderr = StringIO()
            with patch("sys.stderr", stderr):
                code = cmd_configure(root, None, config_path, force=False, generate_after=False)
            self.assertNotEqual(code, 0)
            self.assertIn("--force", stderr.getvalue())


class ConfigureCliTests(unittest.TestCase):
    def test_configure_parse(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["configure", "--force", "--generate"])
        self.assertEqual(args.command, "configure")
        self.assertTrue(args.force)
        self.assertTrue(args.generate)

    def test_configure_end_to_end_with_mocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project></project>", encoding="utf-8")
            with (
                patch("springdocker.configure_wizard.ask_choice", return_value="production-balanced"),
                patch("springdocker.configure_wizard.ask_bool", return_value=True),
            ):
                code = main(["configure", "--project-root", str(root), "--force"])
            self.assertEqual(code, 0)
            config_path = root / ".springdocker.toml"
            loaded = load_config(config_path)
            resolved = resolve_dockerfile_generate_config(*([None] * 21), loaded)
            self.assertEqual(resolved.runtime_image, "distroless")
            self.assertEqual(resolved.profile, "production-balanced")

    def test_configure_respects_build_tool_for_mixed_markers(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "mixed-markers"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "project"
            root.mkdir()
            for name in ("pom.xml", "build.gradle", "gradlew"):
                (root / name).write_text((fixture / name).read_text(encoding="utf-8"), encoding="utf-8")
            with (
                patch("springdocker.configure_wizard.ask_choice", return_value="production-balanced"),
                patch("springdocker.configure_wizard.ask_bool", return_value=True),
            ):
                code = cmd_configure(root, "maven", root / ".springdocker.toml", force=True, generate_after=False)
            self.assertEqual(code, 0)
            loaded = load_config(root / ".springdocker.toml")
            self.assertEqual(loaded["project"]["build_tool"], "maven")


class ConfigureWizardHelperTests(unittest.TestCase):
    def test_ask_choice_returns_default_on_empty_input(self) -> None:
        with patch("builtins.input", return_value=""):
            selected = ask_choice("Pick one:", ["alpha", "beta"], default_index=2)
        self.assertEqual(selected, "beta")

    def test_ask_choice_returns_numeric_selection(self) -> None:
        with patch("builtins.input", return_value="1"):
            selected = ask_choice("Pick one:", ["alpha", "beta"], default_index=2)
        self.assertEqual(selected, "alpha")

    def test_ask_choice_invalid_input_uses_default(self) -> None:
        with patch("builtins.input", return_value="not-a-choice"):
            selected = ask_choice("Pick one:", ["alpha", "beta"], default_index=1)
        self.assertEqual(selected, "alpha")

    def test_ask_bool_returns_default_on_empty_input(self) -> None:
        with patch("builtins.input", return_value=""):
            self.assertTrue(ask_bool("Enable feature?", True))
            self.assertFalse(ask_bool("Enable feature?", False))

    def test_ask_bool_accepts_yes_and_no(self) -> None:
        with patch("builtins.input", return_value="yes"):
            self.assertTrue(ask_bool("Enable feature?", False))
        with patch("builtins.input", return_value="n"):
            self.assertFalse(ask_bool("Enable feature?", True))

    def test_startup_optimization_offers_appcds_on_java_21(self) -> None:
        with patch("springdocker.configure_wizard.ask_choice", return_value="AppCDS") as ask:
            enable_appcds, enable_jep483 = _startup_optimization_choice(21)
        self.assertTrue(enable_appcds)
        self.assertFalse(enable_jep483)
        prompt = ask.call_args.args[0]
        self.assertIn("AppCDS", ask.call_args.args[1])
        self.assertNotIn("JEP 483 AOT cache", ask.call_args.args[1])
        self.assertIn("24", prompt)

    def test_startup_optimization_offers_aot_on_java_25(self) -> None:
        with patch("springdocker.configure_wizard.ask_choice", return_value="JEP 483 AOT cache") as ask:
            enable_appcds, enable_jep483 = _startup_optimization_choice(25)
        self.assertFalse(enable_appcds)
        self.assertTrue(enable_jep483)
        self.assertIn("JEP 483 AOT cache", ask.call_args.args[1])

    def test_startup_optimization_appcds_choice(self) -> None:
        with patch("springdocker.configure_wizard.ask_choice", return_value="AppCDS"):
            enable_appcds, enable_jep483 = _startup_optimization_choice(25)
        self.assertTrue(enable_appcds)
        self.assertFalse(enable_jep483)

    def test_startup_optimization_jep483_choice(self) -> None:
        with patch("springdocker.configure_wizard.ask_choice", return_value="JEP 483 AOT cache"):
            enable_appcds, enable_jep483 = _startup_optimization_choice(25)
        self.assertFalse(enable_appcds)
        self.assertTrue(enable_jep483)

    def test_startup_optimization_none_choice(self) -> None:
        with patch("springdocker.configure_wizard.ask_choice", return_value="none"):
            enable_appcds, enable_jep483 = _startup_optimization_choice(25)
        self.assertFalse(enable_appcds)
        self.assertFalse(enable_jep483)

    def test_edit_jvm_flags_keeps_defaults(self) -> None:
        defaults = ("-XX:MaxRAMPercentage=75",)
        with patch("springdocker.configure_wizard.ask_bool", return_value=True):
            self.assertEqual(_edit_jvm_flags(defaults), defaults)

    def test_edit_jvm_flags_disable_tuned_flags(self) -> None:
        with patch("springdocker.configure_wizard.ask_bool", side_effect=[False, True]):
            self.assertEqual(_edit_jvm_flags(("-XX:MaxRAMPercentage=75",)), ())

    def test_edit_jvm_flags_custom_entry(self) -> None:
        with patch("springdocker.configure_wizard.ask_bool", return_value=False), patch(
            "builtins.input",
            side_effect=["-XX:+UseZGC", ""],
        ):
            self.assertEqual(_edit_jvm_flags(("-XX:MaxRAMPercentage=75",)), ("-XX:+UseZGC",))


class ConfigureWizardFlowTests(unittest.TestCase):
    def test_run_configure_wizard_custom_profile_writes_options(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text(
                "<project><properties><java.version>21</java.version></properties></project>",
                encoding="utf-8",
            )
            config_path = root / ".springdocker.toml"
            with (
                patch(
                    "springdocker.configure_wizard.ask_choice",
                    side_effect=["custom — Custom", "debian-slim", "spring-aot"],
                ),
                patch("springdocker.configure_wizard.ask_bool", return_value=True),
                patch("springdocker.configure_wizard._startup_optimization_choice", return_value=(True, False)),
                patch("builtins.input", return_value=""),
            ):
                resolved = run_configure_wizard(root, config_path)
            text = config_path.read_text("utf-8")
            self.assertEqual(resolved.profile, "custom")
            self.assertEqual(resolved.runtime_image, "debian-slim")
            self.assertEqual(resolved.recipe, "spring-aot")
            self.assertIn('profile = "custom"', text)
            self.assertIn('runtime_image = "debian-slim"', text)
            self.assertIn('recipe = "spring-aot"', text)

    def test_run_configure_wizard_jep483_enables_jlink_for_temurin(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project></project>", encoding="utf-8")
            config_path = root / ".springdocker.toml"
            with (
                patch(
                    "springdocker.configure_wizard.ask_choice",
                    side_effect=["custom — Custom", "temurin", "jvm-balanced"],
                ),
                patch(
                    "springdocker.configure_wizard.ask_bool",
                    side_effect=[
                        False,  # use jlink? (temurin default)
                        True,  # buildkit cache
                        True,  # layered jar
                        True,  # non-root
                        True,  # sbom
                        True,  # pin digests
                        True,  # use default jvm flags
                        True,  # write config
                    ],
                ),
                patch("springdocker.configure_wizard._startup_optimization_choice", return_value=(False, True)),
                patch("builtins.input", return_value="25"),
            ):
                resolved = run_configure_wizard(root, config_path)
            self.assertTrue(resolved.use_jlink)
            self.assertTrue(resolved.enable_jep483_aot_cache)

    def test_run_configure_wizard_fast_cold_start_remaps_to_appcds_on_java_21(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text(
                "<project><properties><java.version>21</java.version></properties></project>",
                encoding="utf-8",
            )
            config_path = root / ".springdocker.toml"
            with (
                patch("springdocker.configure_wizard.ask_choice", return_value="fast-cold-start"),
                patch("springdocker.configure_wizard.ask_bool", return_value=True),
            ):
                resolved = run_configure_wizard(root, config_path)
            self.assertEqual(resolved.profile, "fast-cold-start")
            self.assertFalse(resolved.enable_jep483_aot_cache)
            self.assertTrue(resolved.enable_appcds)

    def test_run_configure_wizard_cancelled_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project></project>", encoding="utf-8")
            config_path = root / ".springdocker.toml"
            with (
                patch("springdocker.configure_wizard.ask_choice", return_value="production-balanced"),
                patch("springdocker.configure_wizard.ask_bool", return_value=False),self.assertRaises(SystemExit)
            ):
                run_configure_wizard(root, config_path)
            self.assertFalse(config_path.exists())

    def test_run_configure_wizard_generate_after_hint(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pom.xml").write_text("<project></project>", encoding="utf-8")
            config_path = root / ".springdocker.toml"
            stdout = StringIO()
            with (
                patch("springdocker.configure_wizard.ask_choice", return_value="production-balanced"),
                patch("springdocker.configure_wizard.ask_bool", return_value=True),
                patch("sys.stdout", stdout),
            ):
                run_configure_wizard(root, config_path, generate_after=True)
            self.assertIn("next: springdocker dockerfile generate", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
