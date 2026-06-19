from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.config import load_config, resolve_dockerfile_generate_config
from springdocker.config_serializer import (
    dockerfile_options_to_table,
    load_existing_config,
    merge_dockerfile_section,
    render_dockerfile_section,
)
from springdocker.dockerfile import DEFAULT_JVM_FLAGS, DockerfileOptions
from springdocker.dockerfile_profiles import apply_profile


class ConfigSerializerTests(unittest.TestCase):
    def test_dockerfile_options_to_table_includes_profile(self) -> None:
        options = apply_profile(DockerfileOptions(build_tool="maven"), "production-balanced")
        table = dockerfile_options_to_table(options, profile="production-balanced")
        self.assertEqual(table["profile"], "production-balanced")
        self.assertEqual(table["runtime_image"], "distroless")

    def test_render_dockerfile_section_includes_jvm_flags(self) -> None:
        table = dockerfile_options_to_table(
            DockerfileOptions(build_tool="maven", jvm_flags=DEFAULT_JVM_FLAGS, tuned_jvm_flags=False),
        )
        rendered = render_dockerfile_section(table)
        self.assertIn("-XX:MaxRAMPercentage=75", rendered)
        self.assertTrue(rendered.startswith("[dockerfile]\n"))

    def test_merge_dockerfile_section_inserts_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / ".springdocker.toml"
            path.write_text("[project]\nbuild_tool = \"maven\"\n", encoding="utf-8")
            table = dockerfile_options_to_table(DockerfileOptions(build_tool="maven"))
            merge_dockerfile_section(path, table)
            text = path.read_text("utf-8")
            self.assertIn("[project]", text)
            self.assertIn("[dockerfile]", text)
            self.assertIn('recipe = "jvm-balanced"', text)

    def test_merge_dockerfile_section_preserves_other_sections(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / ".springdocker.toml"
            path.write_text(
                "[project]\nbuild_tool = \"maven\"\n\n[benchmark.run]\nprofile = \"quick\"\n",
                encoding="utf-8",
            )
            options = apply_profile(DockerfileOptions(build_tool="maven"), "production-balanced")
            merge_dockerfile_section(path, dockerfile_options_to_table(options, profile="production-balanced"))
            text = path.read_text("utf-8")
            self.assertIn("[project]", text)
            self.assertIn("[benchmark.run]", text)
            self.assertIn('runtime_image = "distroless"', text)
            self.assertIn('profile = "production-balanced"', text)

    def test_merge_dockerfile_section_replaces_existing_block(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / ".springdocker.toml"
            path.write_text(
                "[dockerfile]\noutput = \"old\"\njava_version = 21\n\n[project]\nbuild_tool = \"maven\"\n",
                encoding="utf-8",
            )
            table = dockerfile_options_to_table(
                DockerfileOptions(build_tool="maven", java_version=25, runtime_image="alpine")
            )
            merge_dockerfile_section(path, table)
            text = path.read_text("utf-8")
            self.assertNotIn('output = "old"', text)
            self.assertIn("java_version = 25", text)
            self.assertIn('runtime_image = "alpine"', text)
            self.assertIn("[project]", text)

    def test_round_trip_through_config_loader(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / ".springdocker.toml"
            options = DockerfileOptions(
                build_tool="maven",
                java_version=25,
                runtime_image="debian-slim",
                pin_digests=False,
                enable_appcds=False,
            )
            merge_dockerfile_section(path, dockerfile_options_to_table(options))
            loaded = load_config(path, strict=True)
            resolved = resolve_dockerfile_generate_config(
                *[None] * 21,
                loaded,
            )
            self.assertEqual(resolved.java_version, 25)
            self.assertEqual(resolved.runtime_image, "debian-slim")
            self.assertFalse(resolved.pin_digests)
            self.assertFalse(resolved.enable_appcds)

    def test_load_existing_config_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(load_existing_config(Path(td) / "missing.toml"), {})


if __name__ == "__main__":
    unittest.main()
