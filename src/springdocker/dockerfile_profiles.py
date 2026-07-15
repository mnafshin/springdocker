"""Named Dockerfile option bundles for config-first workflows."""

from __future__ import annotations

from dataclasses import replace
from typing import Final, TypedDict

from springdocker.dockerfile import DEFAULT_JVM_FLAGS, DockerfileOptions
from springdocker.java_features import JEP483_MIN_JAVA, jep483_supported


class _ProfileOverlay(TypedDict, total=False):
    runtime_image: str
    use_jlink: bool
    use_layered_jar: bool
    enable_appcds: bool
    enable_jep483_aot_cache: bool
    include_oci_labels: bool
    include_stopsignal: bool
    include_embedded_sbom: bool
    include_reproducible_controls: bool
    pin_digests: bool
    non_root: bool
    tuned_jvm_flags: bool


PROFILE_NAMES: Final[tuple[str, ...]] = (
    "production-balanced",
    "smallest-image",
    "fast-cold-start",
    "build-speed",
    "simplest",
    "compliance",
    "custom",
)

_PROFILE_OVERLAYS: dict[str, _ProfileOverlay] = {
    "production-balanced": {
        "runtime_image": "distroless",
        "use_jlink": True,
        "use_layered_jar": True,
        "enable_appcds": True,
        "enable_jep483_aot_cache": False,
        "include_embedded_sbom": True,
        "pin_digests": True,
        "tuned_jvm_flags": True,
    },
    "smallest-image": {
        "runtime_image": "alpine",
        "use_jlink": True,
        "use_layered_jar": True,
        "enable_appcds": False,
        "enable_jep483_aot_cache": False,
        "tuned_jvm_flags": True,
    },
    "fast-cold-start": {
        "runtime_image": "distroless",
        "use_jlink": True,
        "use_layered_jar": True,
        "enable_appcds": False,
        "enable_jep483_aot_cache": True,
        "include_embedded_sbom": True,
        "pin_digests": True,
        "tuned_jvm_flags": True,
    },
    "build-speed": {
        "runtime_image": "debian-slim",
        "use_jlink": False,
        "use_layered_jar": True,
        "enable_appcds": False,
        "enable_jep483_aot_cache": False,
        "tuned_jvm_flags": True,
    },
    "simplest": {
        "runtime_image": "temurin",
        "use_jlink": False,
        "use_layered_jar": False,
        "enable_appcds": False,
        "enable_jep483_aot_cache": False,
        "tuned_jvm_flags": True,
    },
    "compliance": {
        "runtime_image": "distroless",
        "use_jlink": True,
        "use_layered_jar": True,
        "enable_appcds": False,
        "enable_jep483_aot_cache": False,
        "include_oci_labels": True,
        "include_stopsignal": True,
        "include_embedded_sbom": True,
        "include_reproducible_controls": True,
        "pin_digests": True,
        "non_root": True,
        "tuned_jvm_flags": True,
    },
}


def apply_profile(base: DockerfileOptions, profile: str) -> DockerfileOptions:
    if profile == "custom":
        return base
    if profile not in _PROFILE_OVERLAYS:
        supported = ", ".join(PROFILE_NAMES)
        raise ValueError(f"unknown dockerfile profile: {profile} (expected one of: {supported})")
    overlay = _PROFILE_OVERLAYS[profile]
    return replace(base, **overlay)


def apply_profile_for_java(
    base: DockerfileOptions,
    profile: str,
    java_version: int,
) -> tuple[DockerfileOptions, str | None]:
    """Apply a profile, remapping Java-gated options when needed.

    ``fast-cold-start`` requests JEP 483 AOT on Java 24+. On Java 17–23 it
    remaps to AppCDS and returns a one-line warning.
    """
    options = apply_profile(replace(base, java_version=java_version), profile)
    if profile == "fast-cold-start" and not jep483_supported(java_version):
        options = replace(options, enable_jep483_aot_cache=False, enable_appcds=True)
        warning = (
            f"JEP 483 requires Java {JEP483_MIN_JAVA}+; "
            f"fast-cold-start remapped to AppCDS for Java {java_version}."
        )
        return options, warning
    return options, None


def profile_description(profile: str) -> str:
    descriptions = {
        "production-balanced": "distroless + jlink + supply-chain defaults (team standard)",
        "smallest-image": "alpine + jlink for minimum image size",
        "fast-cold-start": (
            "distroless + jlink + JEP 483 AOT (Java 24+); AppCDS fallback on Java 17–23"
        ),
        "build-speed": "debian-slim without jlink for faster image builds",
        "simplest": "temurin JRE fat JAR — lowest complexity",
        "compliance": "SBOM, digest pins, OCI labels, reproducible controls",
        "custom": "answer each option individually",
    }
    return descriptions.get(profile, profile)


def default_jvm_flags_for_display() -> tuple[str, ...]:
    return DEFAULT_JVM_FLAGS
