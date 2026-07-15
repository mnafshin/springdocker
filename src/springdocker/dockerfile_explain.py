"""
Static Dockerfile explanation helpers.

Parses generated or hand-written Dockerfiles and reports recognized optimizations
using text heuristics (regex and keyword matching). Output is **advisory** — it
does not prove security, correctness, or runtime behavior. For tool-backed CI
gates, use ``springdocker verify`` instead.
"""

from __future__ import annotations

import re

from .dockerfile import JLINK_BASELINE_MODULES


def explain_dockerfile_text(text: str) -> dict[str, object]:
    lines = text.splitlines()
    header_match = re.search(r"# Java (\d+) \| build-tool: (maven|gradle)", text)
    java_version = int(header_match.group(1)) if header_match else None
    build_tool = header_match.group(2) if header_match else None
    if java_version is None:
        image_match = re.search(r"(?im)^\s*FROM\s+[^:\s]+:(\d+)", text)
        if image_match:
            java_version = int(image_match.group(1))
    if build_tool is None:
        lowered = text.lower()
        if "mvnw" in lowered or "maven" in lowered:
            build_tool = "maven"
        elif "gradlew" in lowered or "gradle" in lowered:
            build_tool = "gradle"

    features: list[dict[str, object]] = []
    if sum(1 for line in lines if line.strip().upper().startswith("FROM ")) >= 2:
        features.append(
            {
                "name": "multi-stage build",
                "enabled": True,
                "reason": "Separates the build stage from the runtime stage.",
            }
        )
    if "jdeps" in text and "jlink" in text:
        features.append(
            {
                "name": "jlink runtime",
                "enabled": True,
                "reason": "Builds a smaller custom runtime from the detected module list.",
            }
        )
    if "--mount=type=cache" in text:
        features.append(
            {
                "name": "BuildKit cache",
                "enabled": True,
                "reason": "Caches Maven or Gradle dependencies between builds.",
            }
        )
    if "TARGETPLATFORM" in text and "BUILDPLATFORM" in text:
        features.append(
            {
                "name": "multi-architecture build",
                "enabled": True,
                "reason": "Uses Buildx platform arguments for arm64 and amd64 builds.",
            }
        )
    if "gcr.io/distroless" in text:
        features.append(
            {
                "name": "distroless runtime",
                "enabled": True,
                "reason": "Uses a minimal distroless runtime image.",
            }
        )
    if "debian:bookworm-slim" in text:
        features.append(
            {
                "name": "debian-slim runtime",
                "enabled": True,
                "reason": "Uses a Debian bookworm-slim runtime base image.",
            }
        )
    if re.search(r"(?m)^FROM\s+ubuntu:", text):
        features.append(
            {
                "name": "ubuntu runtime",
                "enabled": True,
                "reason": "Uses an Ubuntu runtime base image.",
            }
        )
    if re.search(r"(?m)^FROM\s+alpine:", text):
        features.append(
            {
                "name": "alpine runtime",
                "enabled": True,
                "reason": "Uses an Alpine runtime base image.",
            }
        )
    if "VOLUME /tmp" in text:
        features.append(
            {
                "name": "read-only filesystem ready",
                "enabled": True,
                "reason": "Keeps /tmp writable when the container root filesystem is read-only.",
            }
        )
    if "USER 1001" in text or "USER nonroot" in text or "gcr.io/distroless" in text:
        features.append(
            {
                "name": "non-root runtime",
                "enabled": True,
                "reason": "Runs the application as an unprivileged container user.",
            }
        )
    if "-XX:MaxRAMPercentage=75" in text:
        features.append(
            {
                "name": "tuned JVM flags",
                "enabled": True,
                "reason": "Applies container-friendly JVM memory and failure defaults.",
            }
        )
    if (
        ("jarmode=tools" in text and "extract --layers" in text)
        or ("jarmode=layertools" in text)
    ) and "/layers/application/" in text:
        features.append(
            {
                "name": "layered jar",
                "enabled": True,
                "reason": "Extracts Spring Boot layers for better image cache reuse.",
            }
        )

    must_have_match = re.search(r'ARG MUSTHAVE_MODULES="([^"]*)"', text)
    must_have_modules = tuple(
        module for module in (part.strip() for part in (must_have_match.group(1) if must_have_match else "").split(",")) if module
    )
    baseline_set = set(JLINK_BASELINE_MODULES)
    baseline_modules = tuple(module for module in must_have_modules if module in baseline_set)
    curated_modules = tuple(module for module in must_have_modules if module not in baseline_set)
    jlink_modules: dict[str, list[str]] = {
        "baseline": list(baseline_modules),
        "curated": list(curated_modules),
    }
    if baseline_modules:
        features.append(
            {
                "name": "jlink baseline modules",
                "enabled": True,
                "reason": (
                    "Auto-injects built-in modules ("
                    + ", ".join(baseline_modules)
                    + ") for Spring/logging/desktop edge cases jdeps often misses."
                ),
                "modules": list(baseline_modules),
            }
        )
    if curated_modules:
        features.append(
            {
                "name": "must-have modules",
                "enabled": True,
                "reason": (
                    "Includes user-curated modules ("
                    + ", ".join(curated_modules)
                    + ") from must-have file that jdeps cannot infer reliably."
                ),
                "modules": list(curated_modules),
            }
        )

    summary_parts = []
    if build_tool and java_version is not None:
        summary_parts.append(f"This {build_tool} Dockerfile targets Java {java_version}.")
    if any(feature["name"] == "multi-stage build" for feature in features):
        summary_parts.append("It uses a multi-stage build to keep the runtime image separate from compilation.")
    if any(feature["name"] == "jlink runtime" for feature in features):
        summary_parts.append("It builds a custom runtime with jlink.")
    if any(feature["name"] == "non-root runtime" for feature in features):
        summary_parts.append("It runs as a non-root user.")
    if any(feature["name"] == "BuildKit cache" for feature in features):
        summary_parts.append("It uses BuildKit cache mounts to speed up repeat builds.")
    if any(feature["name"] == "multi-architecture build" for feature in features):
        summary_parts.append("It is Buildx-friendly for amd64 and arm64 image builds.")
    if any(feature["name"] == "read-only filesystem ready" for feature in features):
        summary_parts.append("It keeps /tmp writable for read-only root filesystem deployments.")
    if any(feature["name"] == "tuned JVM flags" for feature in features):
        summary_parts.append("It applies container-oriented JVM defaults.")
    if baseline_modules:
        summary_parts.append("It merges built-in jlink baseline modules for common Spring framework needs.")
    if curated_modules:
        summary_parts.append("It adds curated modules for reflection or dynamic-loading edge cases.")

    if not summary_parts:
        summary_parts.append("No recognized springdocker optimizations were detected.")

    notes = [
        "Advisory static analysis only — regex/heuristic text matching, not a security or correctness audit.",
        "Hand-written or edited Dockerfiles may be misread; absence of a feature does not mean it is disabled at runtime.",
        "For CI gates (hadolint, trivy, config SSOT drift), use: springdocker verify --check-config-drift",
    ]
    if "HEALTHCHECK" in text:
        features.append(
            {
                "name": "container healthcheck",
                "enabled": True,
                "reason": "Defines a runtime health probe for orchestrators and local checks.",
            }
        )
    if "STOPSIGNAL SIGTERM" in text:
        features.append(
            {
                "name": "explicit stop signal",
                "enabled": True,
                "reason": "Sets explicit signal semantics for clean shutdown behavior.",
            }
        )
    if "org.opencontainers.image.source" in text:
        features.append(
            {
                "name": "OCI image labels",
                "enabled": True,
                "reason": "Includes standard OCI metadata labels for provenance and traceability.",
            }
        )
    if "/usr/share/sbom/spdx.json" in text:
        features.append(
            {
                "name": "embedded SBOM",
                "enabled": True,
                "reason": "Embeds an SPDX JSON file into the container image filesystem.",
            }
        )
    if "SOURCE_DATE_EPOCH" in text:
        features.append(
            {
                "name": "reproducible build controls",
                "enabled": True,
                "reason": "Uses SOURCE_DATE_EPOCH controls for build reproducibility.",
            }
        )
    if "ArchiveClassesAtExit" in text or "SharedArchiveFile=/app/app.jsa" in text:
        features.append(
            {
                "name": "AppCDS training run",
                "enabled": True,
                "reason": "Builds and uses a CDS archive for faster startup.",
            }
        )
    if "AOTCacheOutput" in text or "AOTCache=" in text:
        features.append(
            {
                "name": "JEP 483 AOT cache",
                "enabled": True,
                "reason": "Trains and loads a JEP 483 ahead-of-time class-loading cache.",
            }
        )
    if "native-image-community" in text or "nativeCompile" in text or "native:compile" in text:
        features.append(
            {
                "name": "native AOT build",
                "enabled": True,
                "reason": "Build stage compiles a GraalVM native image.",
            }
        )
    if "processAot" in text or "spring-boot:process-aot" in text:
        features.append(
            {
                "name": "Spring AOT processing",
                "enabled": True,
                "reason": "Build stage runs Spring AOT processing before packaging.",
            }
        )

    return {
        "source": "Dockerfile",
        "build_tool": build_tool,
        "java_version": java_version,
        "stage_count": sum(1 for line in lines if line.strip().upper().startswith("FROM ")),
        "features": features,
        "jlink_modules": jlink_modules,
        "summary": " ".join(summary_parts),
        "notes": notes,
    }
