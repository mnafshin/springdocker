"""springdocker CLI package."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]
try:
    __version__ = version("springdocker")
except PackageNotFoundError:  # pragma: no cover - local source tree fallback
    __version__ = "1.2.0"
