from __future__ import annotations

DEFAULT_BASE_IMAGE_VARIANTS: tuple[str, ...] = (
    "alpine",
    "debian-slim",
    "ubuntu",
    "distroless",
)

_RUNTIME_ALIASES: dict[str, str] = {
    "alpine": "alpine",
    "debian-slim": "debian-slim",
    "debian-bookworm-slim": "debian-slim",
    "ubuntu": "ubuntu",
    "ubuntu-noble": "ubuntu",
    "distroless": "distroless",
    "distroless-nonroot": "distroless",
    "temurin": "temurin",
    "temurin-jre": "temurin",
    "eclipse-temurin-jre": "temurin",
}

SUPPORTED_RUNTIME_IMAGES: frozenset[str] = frozenset(_RUNTIME_ALIASES.values())


def normalize_runtime_image(name: str) -> str:
    """Map config or CLI names to a supported runtime_image value."""
    key = name.strip().lower().replace("_", "-")
    normalized = _RUNTIME_ALIASES.get(key)
    if normalized is None:
        supported = ", ".join(sorted(SUPPORTED_RUNTIME_IMAGES))
        raise ValueError(f"unknown runtime base {name!r}; supported: {supported}")
    return normalized


def variant_slug(name: str) -> str:
    """Directory-safe variant name for benchmark output."""
    return normalize_runtime_image(name)


def parse_base_image_variants(values: list[str] | None) -> tuple[str, ...]:
    """Parse and de-duplicate configured base-image variant names."""
    if not values:
        return DEFAULT_BASE_IMAGE_VARIANTS
    seen: set[str] = set()
    parsed: list[str] = []
    for raw in values:
        normalized = normalize_runtime_image(raw)
        if normalized in seen:
            continue
        seen.add(normalized)
        parsed.append(normalized)
    if not parsed:
        raise ValueError("base image choice must define at least one variant")
    return tuple(parsed)
