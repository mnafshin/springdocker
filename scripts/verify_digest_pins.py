#!/usr/bin/env python3
"""Verify springdocker base-image digest pins resolve in upstream registries."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from springdocker.digest_pins import IMAGE_PINS, verify_all_image_pins


def main() -> int:
    print(f"Verifying {len(IMAGE_PINS)} pinned base images...")
    try:
        verify_all_image_pins()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    print("All digest pins resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
