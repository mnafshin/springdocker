"""Java version feature availability for springdocker.

Floor is Java 17. JEP 483 AOT cache requires Java 24+.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from springdocker.dockerfile import DockerfileOptions

MIN_JAVA_VERSION = 17
JEP483_MIN_JAVA = 24


@dataclass(frozen=True)
class FeatureAvailability:
    """Which Dockerfile features are valid for a given major Java version."""

    java_version: int
    jlink: bool
    appcds: bool
    layered_jar: bool
    tuned_jvm_flags: bool
    jep483_aot_cache: bool
    native_aot_recipe: bool


def assert_java_supported(java_version: int) -> None:
    if java_version < MIN_JAVA_VERSION:
        raise ValueError(f"java version must be >= {MIN_JAVA_VERSION} (got {java_version})")


def jep483_supported(java_version: int) -> bool:
    return java_version >= JEP483_MIN_JAVA


def features_for(java_version: int) -> FeatureAvailability:
    assert_java_supported(java_version)
    return FeatureAvailability(
        java_version=java_version,
        jlink=True,
        appcds=True,
        layered_jar=True,
        tuned_jvm_flags=True,
        jep483_aot_cache=jep483_supported(java_version),
        native_aot_recipe=True,
    )


def validate_dockerfile_options(options: DockerfileOptions) -> None:
    """Hard-fail on unsupported Java feature combinations."""
    assert_java_supported(options.java_version)
    if options.enable_jep483_aot_cache and not jep483_supported(options.java_version):
        raise ValueError(
            f"JEP 483 AOT cache requires Java {JEP483_MIN_JAVA} or newer "
            f"(java_version={options.java_version})"
        )
    if options.enable_jep483_aot_cache and not options.use_jlink:
        raise ValueError("JEP 483 AOT cache requires use_jlink=True")
    if options.enable_jep483_aot_cache and options.enable_appcds:
        raise ValueError("enable_jep483_aot_cache and enable_appcds are mutually exclusive")
