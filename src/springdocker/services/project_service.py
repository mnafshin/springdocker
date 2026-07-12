from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import render_default_config, write_default_config
from ..project_detect import InspectInfo, ProjectInfo, inspect_project, inspect_project_details


def load_project_info(project_root: Path, build_tool: str | None) -> ProjectInfo:
    return inspect_project(project_root, build_tool)


def load_project_details(project_root: Path, build_tool: str | None) -> InspectInfo:
    return inspect_project_details(project_root, build_tool)


@dataclass(frozen=True)
class InitConfigResult:
    rendered: str | None
    written_path: Path | None


def prepare_default_config(
    project_root: Path,
    build_tool: str | None,
    config_path: Path,
    profile: str,
    force: bool,
    print_only: bool,
) -> InitConfigResult:
    info = inspect_project(project_root, build_tool)
    if print_only:
        return InitConfigResult(rendered=render_default_config(build_tool=info.build_tool, profile=profile), written_path=None)
    write_default_config(path=config_path, build_tool=info.build_tool, profile=profile, force=force)
    return InitConfigResult(rendered=None, written_path=config_path)

