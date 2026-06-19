from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .plugins import detect_build_tool_from_plugins


@dataclass(frozen=True)
class ProjectInfo:
    root: Path
    build_tool: str
    has_spring_markers: bool


SPRING_WEB_STARTER_ARTIFACTS: tuple[str, ...] = (
    "spring-boot-starter-web",
    "spring-boot-starter-webflux",
    "spring-boot-starter-websocket",
)


@dataclass(frozen=True)
class MultiModuleLayout:
    kind: str
    modules: tuple[str, ...]
    spring_boot_modules: tuple[str, ...]


@dataclass(frozen=True)
class InspectInfo:
    root: Path
    build_tool: str
    has_spring_markers: bool
    java_version: int | None
    spring_boot_version: str | None
    direct_dependencies: tuple[str, ...]
    config_exists: bool
    generated_dockerfiles: tuple[str, ...]
    reflection_hits: tuple[str, ...]
    runtime_compatibility: str
    recommendations: tuple[str, ...]
    layout: str
    modules: tuple[str, ...]
    spring_boot_modules: tuple[str, ...]


def detect_build_tool(root: Path, explicit: str | None = None) -> str:
    """Detect Maven or Gradle build tool from project markers."""
    if explicit:
        if explicit not in {"maven", "gradle"}:
            raise ValueError("build tool must be 'maven' or 'gradle'")
        return explicit

    plugin_detected = detect_build_tool_from_plugins(root)
    if plugin_detected is not None:
        return plugin_detected

    has_maven = (root / "pom.xml").exists()
    has_gradle = (root / "gradlew").exists() or any(
        (root / name).exists() for name in ("build.gradle", "build.gradle.kts")
    )

    if has_maven and has_gradle:
        raise ValueError(
            "Both Maven and Gradle markers found. Pass --build-tool explicitly."
        )
    if has_maven:
        return "maven"
    if has_gradle:
        return "gradle"
    raise ValueError("Could not detect build tool. Expected pom.xml or gradle markers.")


def has_spring_web_dependency(root: Path, build_tool: str | None = None) -> bool:
    """Return True when the project declares a Spring Web stack starter."""
    if _descriptor_has_web_starter(root):
        return True
    try:
        tool = build_tool or detect_build_tool(root)
    except ValueError:
        return False
    layout = analyze_multi_module_layout(root, tool)
    return any(_descriptor_has_web_starter(root / module) for module in layout.spring_boot_modules)


def _descriptor_has_web_starter(root: Path) -> bool:
    for descriptor in ("pom.xml", "build.gradle", "build.gradle.kts"):
        path = root / descriptor
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(artifact in text for artifact in SPRING_WEB_STARTER_ARTIFACTS):
            return True
    return False


def _direct_spring_markers(root: Path) -> bool:
    """Spring Boot markers in this directory only (not child modules)."""
    if (root / "src" / "main" / "resources" / "application.properties").exists():
        return True
    if (root / "src" / "main" / "resources" / "application.yml").exists():
        return True

    for descriptor in ("pom.xml", "build.gradle", "build.gradle.kts"):
        path = root / descriptor
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "spring-boot" in text or "org.springframework.boot" in text:
            return True
    return False


def has_spring_project_markers(root: Path, build_tool: str | None = None) -> bool:
    """Best-effort Spring Boot marker detection for Java projects."""
    if _direct_spring_markers(root):
        return True
    try:
        tool = build_tool or detect_build_tool(root)
    except ValueError:
        return False
    layout = analyze_multi_module_layout(root, tool)
    return bool(layout.spring_boot_modules)


def _parse_maven_pom(root: Path) -> ET.Element | None:
    pom = root / "pom.xml"
    if not pom.exists():
        return None
    try:
        tree = ET.parse(pom)
    except ET.ParseError:
        return None
    xml_root = tree.getroot()
    _strip_namespace(xml_root)
    return xml_root


def _list_maven_reactor_modules(root: Path) -> tuple[str, ...]:
    xml_root = _parse_maven_pom(root)
    if xml_root is None:
        return ()
    packaging = (xml_root.findtext("packaging") or "jar").strip()
    modules_el = xml_root.find("modules")
    if packaging != "pom" or modules_el is None:
        return ()
    modules: list[str] = []
    for module in modules_el.findall("module"):
        if module.text:
            name = module.text.strip()
            if name and (root / name / "pom.xml").exists():
                modules.append(name)
    return tuple(modules)


_GRADLE_INCLUDE_RE = re.compile(r"""include\s*(?:\(|[^\S\r\n]*)\s*['"]([^'"]+)['"]""")


def _list_gradle_subprojects(root: Path) -> tuple[str, ...]:
    for candidate in ("settings.gradle.kts", "settings.gradle"):
        path = root / candidate
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        modules: list[str] = []
        seen: set[str] = set()
        for match in _GRADLE_INCLUDE_RE.finditer(text):
            raw = match.group(1).strip()
            module_path = raw.replace(":", "/")
            if module_path in seen:
                continue
            if (root / module_path / "build.gradle").exists() or (root / module_path / "build.gradle.kts").exists():
                seen.add(module_path)
                modules.append(module_path)
        if modules:
            return tuple(modules)
    return ()


def analyze_multi_module_layout(root: Path, build_tool: str) -> MultiModuleLayout:
    if build_tool == "maven":
        modules = _list_maven_reactor_modules(root)
        if not modules:
            return MultiModuleLayout("single-module", (), ())
        spring_boot_modules = tuple(module for module in modules if _direct_spring_markers(root / module))
        return MultiModuleLayout("maven-reactor", modules, spring_boot_modules)
    modules = _list_gradle_subprojects(root)
    if not modules:
        return MultiModuleLayout("single-module", (), ())
    spring_boot_modules = tuple(module for module in modules if _direct_spring_markers(root / module))
    return MultiModuleLayout("gradle-multi-project", modules, spring_boot_modules)


def _layout_recommendations(layout: MultiModuleLayout, root: Path) -> list[str]:
    notes: list[str] = []
    if layout.kind == "single-module":
        return notes
    if not layout.modules:
        return notes
    notes.append(
        f"Detected {layout.kind} layout with modules: {', '.join(layout.modules)}."
    )
    if layout.spring_boot_modules:
        if len(layout.spring_boot_modules) == 1:
            module = layout.spring_boot_modules[0]
            if not _direct_spring_markers(root):
                notes.append(
                    f"Spring Boot app appears to live in `{module}` — run springdocker with "
                    f"`--project-root {root / module}` for Dockerfile generation."
                )
        else:
            joined = ", ".join(f"`{item}`" for item in layout.spring_boot_modules)
            notes.append(
                f"Multiple Spring Boot modules detected ({joined}); point --project-root at the service you containerize."
            )
    elif layout.kind in {"maven-reactor", "gradle-multi-project"}:
        notes.append(
            "No Spring Boot markers found in listed modules; verify --project-root or add a project_detectors plugin."
        )
    return notes


def inspect_project(root: Path, explicit_build_tool: str | None = None) -> ProjectInfo:
    build_tool = detect_build_tool(root, explicit_build_tool)
    layout = analyze_multi_module_layout(root, build_tool)
    has_spring = _direct_spring_markers(root) or bool(layout.spring_boot_modules)
    return ProjectInfo(
        root=root,
        build_tool=build_tool,
        has_spring_markers=has_spring,
    )


def _strip_namespace(element: ET.Element) -> None:
    for child in element.iter():
        if "}" in child.tag:
            child.tag = child.tag.split("}", 1)[1]


def _parse_int(text: str | None) -> int | None:
    if text is None:
        return None
    match = re.search(r"\d+", text)
    if not match:
        return None
    return int(match.group(0))


def _extract_maven_info(root: Path) -> tuple[int | None, str | None, tuple[str, ...]]:
    xml_root = _parse_maven_pom(root)
    if xml_root is None:
        return None, None, ()

    java_version = None
    properties = xml_root.find("properties")
    if properties is not None:
        for key in ("java.version", "maven.compiler.release", "maven.compiler.source", "maven.compiler.target"):
            java_version = _parse_int(properties.findtext(key))
            if java_version is not None:
                break

    spring_boot_version = None
    parent = xml_root.find("parent")
    if parent is not None:
        version = parent.findtext("version")
        if version:
            spring_boot_version = version.strip()
    if spring_boot_version is None:
        deps = xml_root.find("dependencyManagement")
        if deps is not None:
            spring_boot_version = None

    dependencies: list[str] = []
    for deps in xml_root.findall("dependencies"):
        for dep in deps.findall("dependency"):
            group = (dep.findtext("groupId") or "").strip()
            artifact = (dep.findtext("artifactId") or "").strip()
            if group and artifact:
                dependencies.append(f"{group}:{artifact}")

    return java_version, spring_boot_version, tuple(dependencies)


def _extract_gradle_info(root: Path) -> tuple[int | None, str | None, tuple[str, ...]]:
    for candidate in ("build.gradle", "build.gradle.kts"):
        path = root / candidate
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")

        spring_boot_version = None
        m = re.search(r"""org\.springframework\.boot['"]\s+version\s+['"]([^'"]+)['"]""", text)
        if m:
            spring_boot_version = m.group(1)

        java_version = None
        for pattern in (
            r"JavaLanguageVersion\.of\((\d+)\)",
            r"sourceCompatibility\s*=\s*['\"]?(\d+)",
            r"targetCompatibility\s*=\s*['\"]?(\d+)",
        ):
            m = re.search(pattern, text)
            if m:
                java_version = int(m.group(1))
                break

        dependencies: list[str] = []
        for dep_match in re.finditer(
            r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation)\s*(?:\(|\s)\s*['"]([^:'"]+):([^:'"]+):([^'"]+)['"]""",
            text,
        ):
            dependencies.append(f"{dep_match.group(1)}:{dep_match.group(2)}")

        return java_version, spring_boot_version, tuple(dependencies)

    return None, None, ()


def _find_reflection_hits(root: Path) -> tuple[str, ...]:
    hits: list[str] = []
    for path in sorted(root.rglob("*.java")):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            if any(token in line for token in ("Class.forName(", "getDeclaredMethod(", "getDeclaredField(", "setAccessible(")):
                hits.append(f"{path.relative_to(root)}:{line_no}:{line.strip()}")
    return tuple(hits)


def _runtime_compatibility(java_version: int | None, spring_boot_version: str | None) -> tuple[str, tuple[str, ...]]:
    recommendations: list[str] = []
    if spring_boot_version is None:
        return "unknown", ("Spring Boot version could not be detected statically.",)

    boot_major = _parse_int(spring_boot_version.split(".", 1)[0])
    if boot_major is None:
        return "unknown", ("Spring Boot version could not be parsed cleanly.",)

    if boot_major >= 4:
        min_java = 21
    elif boot_major >= 3:
        min_java = 17
    else:
        min_java = 8

    if java_version is None:
        recommendations.append("Java version could not be detected statically.")
        return "unknown", tuple(recommendations)

    if java_version < min_java:
        return "incompatible", (f"Spring Boot {spring_boot_version} generally expects Java {min_java}+.",)
    if java_version >= min_java:
        return "compatible", (f"Spring Boot {spring_boot_version} and Java {java_version} look compatible.",)
    return "unknown", ("Compatibility could not be determined.",)


def inspect_project_details(root: Path, explicit_build_tool: str | None = None) -> InspectInfo:
    project = inspect_project(root, explicit_build_tool)
    layout = analyze_multi_module_layout(root, project.build_tool)
    metadata_root = root
    if not _direct_spring_markers(root) and len(layout.spring_boot_modules) == 1:
        metadata_root = root / layout.spring_boot_modules[0]

    java_version = None
    spring_boot_version = None
    direct_dependencies: tuple[str, ...] = ()
    if project.build_tool == "maven":
        java_version, spring_boot_version, direct_dependencies = _extract_maven_info(metadata_root)
        if java_version is None and metadata_root != root:
            java_version, spring_boot_version, direct_dependencies = _extract_maven_info(root)
    else:
        java_version, spring_boot_version, direct_dependencies = _extract_gradle_info(metadata_root)
        if java_version is None and metadata_root != root:
            java_version, spring_boot_version, direct_dependencies = _extract_gradle_info(root)

    compatibility, compatibility_notes = _runtime_compatibility(java_version, spring_boot_version)
    config_exists = (root / ".springdocker.toml").exists()
    generated_dockerfiles = tuple(
        str(path.relative_to(root))
        for path in sorted(root.glob("Dockerfile*"))
        if path.is_file()
    )
    reflection_root = metadata_root if metadata_root != root else root
    reflection_hits = _find_reflection_hits(reflection_root)
    recommendations = list(compatibility_notes)
    recommendations.extend(_layout_recommendations(layout, root))
    if not config_exists:
        recommendations.append("Run `springdocker init` to create a starter .springdocker.toml file.")
    if not generated_dockerfiles:
        recommendations.append("No Dockerfile artifacts found in the project root.")
    if not direct_dependencies:
        recommendations.append("No direct dependency list could be extracted statically.")
    if not reflection_hits:
        recommendations.append("No direct reflection calls were found in Java source.")
    else:
        recommendations.append("Direct reflection calls were found in Java source; review them before using jlink.")

    return InspectInfo(
        root=project.root,
        build_tool=project.build_tool,
        has_spring_markers=project.has_spring_markers,
        java_version=java_version,
        spring_boot_version=spring_boot_version,
        direct_dependencies=direct_dependencies,
        config_exists=config_exists,
        generated_dockerfiles=generated_dockerfiles,
        reflection_hits=reflection_hits,
        runtime_compatibility=compatibility,
        recommendations=tuple(recommendations),
        layout=layout.kind,
        modules=layout.modules,
        spring_boot_modules=layout.spring_boot_modules,
    )
