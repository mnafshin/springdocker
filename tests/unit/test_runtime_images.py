from __future__ import annotations

import unittest

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.runtime_images import (
    DEFAULT_BASE_IMAGE_VARIANTS,
    normalize_runtime_image,
    parse_base_image_variants,
    variant_slug,
)


class RuntimeImageConfigTests(unittest.TestCase):
    def test_default_variants(self) -> None:
        self.assertEqual(
            DEFAULT_BASE_IMAGE_VARIANTS,
            ("alpine", "debian-slim", "ubuntu", "distroless"),
        )

    def test_normalize_aliases(self) -> None:
        self.assertEqual(normalize_runtime_image("debian-bookworm-slim"), "debian-slim")
        self.assertEqual(normalize_runtime_image("ubuntu-noble"), "ubuntu")
        self.assertEqual(normalize_runtime_image("eclipse-temurin-jre"), "temurin")
        self.assertEqual(variant_slug("distroless-nonroot"), "distroless")

    def test_parse_deduplicates(self) -> None:
        parsed = parse_base_image_variants(["alpine", "Alpine", "temurin"])
        self.assertEqual(parsed, ("alpine", "temurin"))

    def test_unknown_variant_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_runtime_image("fedora")


if __name__ == "__main__":
    unittest.main()
