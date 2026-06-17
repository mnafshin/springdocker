"""Resolve build tool for Maven reactor roots that only contain aggregator POMs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


def _strip_namespace(element: ET.Element) -> None:
    for child in element.iter():
        if "}" in child.tag:
            child.tag = child.tag.split("}", 1)[1]


def detect_build_tool(project_root: Path) -> str | None:
    pom = project_root / "pom.xml"
    if not pom.exists():
        return None
    try:
        tree = ET.parse(pom)
    except ET.ParseError:
        return None
    root = tree.getroot()
    _strip_namespace(root)
    packaging = (root.findtext("packaging") or "jar").strip()
    modules = root.find("modules")
    if packaging == "pom" and modules is not None and modules.findall("module"):
        return "maven"
    return None
