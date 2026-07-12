from __future__ import annotations

import io
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from tests.test_support import add_src_to_path

add_src_to_path()

from springdocker.digest_pins import (
    DISTROLESS_BASE_DIGESTS,
    IMAGE_PINS,
    OS_RUNTIME_IMAGES,
    TEMURIN_JDK_DIGESTS,
    TEMURIN_JRE_DIGESTS,
    ImagePin,
    verify_all_image_pins,
    verify_image_pin,
)


class DigestPinCatalogTests(unittest.TestCase):
    def test_catalog_covers_temurin_and_distroless_maps(self) -> None:
        self.assertEqual(set(TEMURIN_JDK_DIGESTS), {17, 21, 25})
        self.assertEqual(set(TEMURIN_JRE_DIGESTS), {17, 21, 25})
        self.assertEqual(set(DISTROLESS_BASE_DIGESTS), {12, 13})
        debian_digest = next(pin.digest for pin in IMAGE_PINS if pin.label == "debian-bookworm-slim")
        ubuntu_digest = next(pin.digest for pin in IMAGE_PINS if pin.label == "ubuntu-noble")
        alpine_digest = next(pin.digest for pin in IMAGE_PINS if pin.label == "alpine-3-21")
        self.assertEqual(OS_RUNTIME_IMAGES["debian-slim"], ("debian:bookworm-slim", debian_digest))
        self.assertEqual(OS_RUNTIME_IMAGES["ubuntu"], ("ubuntu:24.04", ubuntu_digest))
        self.assertEqual(OS_RUNTIME_IMAGES["alpine"], ("alpine:3.21", alpine_digest))
        self.assertEqual({pin.label for pin in IMAGE_PINS}, {
            "temurin-jdk-17",
            "temurin-jdk-21",
            "temurin-jdk-25",
            "temurin-jre-17",
            "temurin-jre-21",
            "temurin-jre-25",
            "distroless-java-17",
            "distroless-java-21",
            "distroless-base-debian12",
            "distroless-base-debian13",
            "debian-bookworm-slim",
            "ubuntu-noble",
            "alpine-3-21",
        })

    def test_image_ref_format(self) -> None:
        pin = next(item for item in IMAGE_PINS if item.label == "temurin-jdk-21")
        self.assertEqual(
            pin.image_ref,
            "eclipse-temurin:21-jdk@sha256:b9142586f9712700c6c9e07adcedfb18608b1a3a056e4001423a3354adfa9d80",
        )
        distroless = next(item for item in IMAGE_PINS if item.label == "distroless-base-debian13")
        self.assertTrue(distroless.image_ref.startswith("gcr.io/distroless/base-debian13:nonroot@sha256:"))

    def test_invalid_digest_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ImagePin("bad", "registry-1.docker.io", "library/debian", "bookworm-slim", "not-a-digest")


class DigestPinVerifyTests(unittest.TestCase):
    def test_verify_image_pin_uses_docker_hub_token(self) -> None:
        pin = next(item for item in IMAGE_PINS if item.label == "temurin-jdk-21")
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        opener = MagicMock()
        opener.open.return_value = response

        token_payload = io.BytesIO(b'{"token":"test-token"}')
        with patch("springdocker.digest_pins.urllib.request.urlopen", return_value=token_payload):
            verify_image_pin(pin, opener=opener)

        opener.open.assert_called_once()
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "HEAD")
        self.assertIn("Authorization", request.headers)
        self.assertEqual(request.headers["Authorization"], "Bearer test-token")

    def test_verify_all_image_pins_collects_failures(self) -> None:
        pin = IMAGE_PINS[0]

        def _fail(first: ImagePin, opener=None):  # type: ignore[no-untyped-def]
            if first.label == pin.label:
                raise urllib.error.URLError("offline")

        with patch("springdocker.digest_pins.verify_image_pin", side_effect=_fail), self.assertRaises(RuntimeError) as ctx:
            verify_all_image_pins()
        self.assertIn(pin.label, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
