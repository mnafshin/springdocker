"""Pinned base-image digests used by Dockerfile generation."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass

_DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")


@dataclass(frozen=True)
class ImagePin:
    """A tag+digest pin checked against a container registry."""

    label: str
    registry_host: str
    repository_path: str
    tag: str
    digest: str

    def __post_init__(self) -> None:
        if not _DIGEST_RE.fullmatch(self.digest):
            raise ValueError(f"invalid digest for {self.label}: {self.digest}")

    @property
    def image_ref(self) -> str:
        if self.registry_host == "registry-1.docker.io":
            short_repo = self.repository_path.removeprefix("library/")
            return f"{short_repo}:{self.tag}@{self.digest}"
        return f"{self.registry_host}/{self.repository_path}:{self.tag}@{self.digest}"

    def manifest_url(self) -> str:
        return f"https://{self.registry_host}/v2/{self.repository_path}/manifests/{self.digest}"


# Renovate regex manager matches ImagePin(...) rows in this tuple (see .github/renovate.json).
IMAGE_PINS: tuple[ImagePin, ...] = (
    ImagePin("temurin-jdk-17", "registry-1.docker.io", "library/eclipse-temurin", "17-jdk", "sha256:b04a8c5d46e210873ffd1af6ad5f4d62c69ed3a6736993556eae60bba1373a23"),
    ImagePin("temurin-jdk-21", "registry-1.docker.io", "library/eclipse-temurin", "21-jdk", "sha256:b9142586f9712700c6c9e07adcedfb18608b1a3a056e4001423a3354adfa9d80"),
    ImagePin("temurin-jdk-25", "registry-1.docker.io", "library/eclipse-temurin", "25-jdk", "sha256:c2b7ea21649875fb9052237ac4e3cd4ef63968a2a389a0a1b1a72a5e53e5c93f"),
    ImagePin("temurin-jre-17", "registry-1.docker.io", "library/eclipse-temurin", "17-jre", "sha256:0d79988c68791ce864fe39d149ab1dc84f680539dca77ee7f6f3b041ad7f2f43"),
    ImagePin("temurin-jre-21", "registry-1.docker.io", "library/eclipse-temurin", "21-jre", "sha256:010e0a06bd4e0184dec58626afb3ba727b42c56c91b977e2f0a9e0837e0fa3fb"),
    ImagePin("temurin-jre-25", "registry-1.docker.io", "library/eclipse-temurin", "25-jre", "sha256:04262e8782d6b034ee5d7c1c5d4e8938fcf2063a76b4bfcd84e5d994d09c27bc"),
    ImagePin("distroless-java-17", "gcr.io", "distroless/java17-debian12", "nonroot", "sha256:06484c2a9dcc9070aeafbc0fe752cb9f73bc0cea5c311f6a516e9010061998ad"),
    ImagePin("distroless-java-21", "gcr.io", "distroless/java21-debian12", "nonroot", "sha256:7e37784d94dccbf5ccb195c73b295f5ad00cd266512dfbac12eb9c3c28f8077d"),
    ImagePin("distroless-base-debian12", "gcr.io", "distroless/base-debian12", "nonroot", "sha256:7a75a36f4bec82a7542c64195e402907486f9a4dd2f8797a976aa0cf31cfb470"),
    ImagePin("distroless-base-debian13", "gcr.io", "distroless/base-debian13", "nonroot", "sha256:ab7554b6d07ad354fad31957f8a1a813e65dfb93a8ad160568c79c3f2be6884f"),
    ImagePin("debian-bookworm-slim", "registry-1.docker.io", "library/debian", "bookworm-slim", "sha256:d5d3f9c23164ea16f31852f95bd5959aad1c5e854332fe00f7b3a20fcc9f635c"),
    ImagePin("ubuntu-noble", "registry-1.docker.io", "library/ubuntu", "24.04", "sha256:52df9b1ee71626e0088f7d400d5c6b5f7bb916f8f0c82b474289a4ece6cf3faf"),
    ImagePin("alpine-3-21", "registry-1.docker.io", "library/alpine", "3.21", "sha256:f27cad9117495d32d067133afff942cb2dc745dfe9163e949f6bfe8a6a245339"),
)


def _build_java_digest_map(prefix: str) -> dict[int, str]:
    return {
        int(pin.label.removeprefix(prefix)): pin.digest
        for pin in IMAGE_PINS
        if pin.label.startswith(prefix)
    }


TEMURIN_JDK_DIGESTS: dict[int, str] = _build_java_digest_map("temurin-jdk-")
TEMURIN_JRE_DIGESTS: dict[int, str] = _build_java_digest_map("temurin-jre-")
DISTROLESS_JAVA_DIGESTS: dict[int, str] = {
    int(pin.label.removeprefix("distroless-java-")): pin.digest
    for pin in IMAGE_PINS
    if pin.label.startswith("distroless-java-")
}
DISTROLESS_BASE_DIGESTS: dict[int, str] = {
    int(pin.label.removeprefix("distroless-base-debian")): pin.digest
    for pin in IMAGE_PINS
    if pin.label.startswith("distroless-base-debian")
}
DEBIAN_BOOKWORM_SLIM_DIGEST: str = next(pin.digest for pin in IMAGE_PINS if pin.label == "debian-bookworm-slim")
UBUNTU_2404_DIGEST: str = next(pin.digest for pin in IMAGE_PINS if pin.label == "ubuntu-noble")
ALPINE_321_DIGEST: str = next(pin.digest for pin in IMAGE_PINS if pin.label == "alpine-3-21")
OS_RUNTIME_IMAGES: dict[str, tuple[str, str | None]] = {
    "debian-slim": ("debian:bookworm-slim", DEBIAN_BOOKWORM_SLIM_DIGEST),
    "ubuntu": ("ubuntu:24.04", UBUNTU_2404_DIGEST),
    "alpine": ("alpine:3.21", ALPINE_321_DIGEST),
}


def iter_image_pins() -> Iterator[ImagePin]:
    yield from IMAGE_PINS


def _docker_hub_token(repository_path: str) -> str:
    scope = f"repository:{repository_path}:pull"
    token_url = f"https://auth.docker.io/token?service=registry.docker.io&scope={scope}"
    with urllib.request.urlopen(token_url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    token = payload.get("token")
    if not isinstance(token, str) or not token:
        raise RuntimeError(f"docker hub token response missing token for {repository_path}")
    return token


_MANIFEST_ACCEPT = (
    "application/vnd.oci.image.index.v1+json, "
    "application/vnd.docker.distribution.manifest.list.v2+json, "
    "application/vnd.docker.distribution.manifest.v2+json, "
    "application/vnd.oci.image.manifest.v1+json"
)


def _request_headers(pin: ImagePin) -> dict[str, str]:
    headers = {
        "Accept": _MANIFEST_ACCEPT,
        "User-Agent": "springdocker-digest-verify",
    }
    if pin.registry_host == "registry-1.docker.io":
        headers["Authorization"] = f"Bearer {_docker_hub_token(pin.repository_path)}"
    return headers


def verify_image_pin(pin: ImagePin, opener: urllib.request.OpenerDirector | None = None) -> None:
    """Raise URLError/HTTPError when the pinned digest cannot be resolved."""
    request = urllib.request.Request(pin.manifest_url(), method="HEAD", headers=_request_headers(pin))
    open_fn = opener.open if opener is not None else urllib.request.urlopen
    with open_fn(request, timeout=30) as response:
        if response.status >= 400:
            raise urllib.error.HTTPError(
                pin.manifest_url(),
                response.status,
                f"manifest lookup failed for {pin.image_ref}",
                response.headers,
                None,
            )


def verify_all_image_pins(opener: urllib.request.OpenerDirector | None = None) -> None:
    failures: list[str] = []
    for pin in IMAGE_PINS:
        try:
            verify_image_pin(pin, opener=opener)
        except (urllib.error.URLError, RuntimeError) as exc:
            failures.append(f"{pin.label} ({pin.image_ref}): {exc}")
    if failures:
        joined = "\n".join(failures)
        raise RuntimeError(f"digest pin verification failed:\n{joined}")
