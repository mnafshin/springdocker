#!/usr/bin/env python3
"""Deprecated wrapper — use springdocker configure + dockerfile generate instead."""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "tools/dockerfile_wizard.py is retired.\n"
        "Use the config-first workflow instead:\n"
        "  springdocker configure --project-root .\n"
        "  springdocker dockerfile generate --project-root .",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
