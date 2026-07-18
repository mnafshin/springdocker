"""Render GitHub Actions workflow files for Dockerfile SSOT checks."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from jinja2 import Template

from springdocker import __version__

DEFAULT_WORKFLOW_RELATIVE = Path(".github") / "workflows" / "dockerfile.yml"
ACTION_USES_TEMPLATE = "mnafshin/springdocker/action@v{major}"


def action_uses_ref(*, package_version: str | None = None) -> str:
    """Return a path-based Action ref pinned to the package major version."""
    version = package_version or __version__
    major = version.split(".", 1)[0]
    if not major.isdigit():
        major = "1"
    return ACTION_USES_TEMPLATE.format(major=major)


def render_dockerfile_ssot_workflow(
    *,
    dockerfile: str = "Dockerfile.generated",
    project_root: str = ".",
    build_tool: str | None = None,
    springdocker_version: str | None = None,
    action_ref: str | None = None,
    pin_version: bool = False,
) -> str:
    """Render the Dockerfile SSOT workflow that uses the springdocker Action."""
    template_text = (
        resources.files("springdocker")
        .joinpath("templates/github_dockerfile_workflow.yml.j2")
        .read_text(encoding="utf-8")
    )
    if springdocker_version is not None:
        pinned_version = springdocker_version
    elif pin_version:
        pinned_version = __version__
    else:
        pinned_version = ""
    return Template(template_text).render(
        action_ref=action_ref or action_uses_ref(package_version=pinned_version or __version__),
        dockerfile=dockerfile,
        project_root=project_root,
        build_tool=build_tool or "",
        springdocker_version=pinned_version,
    )


def write_dockerfile_ssot_workflow(
    project_root: Path,
    *,
    dockerfile: str = "Dockerfile.generated",
    build_tool: str | None = None,
    force: bool = False,
    workflow_path: Path | None = None,
) -> Path:
    """Write `.github/workflows/dockerfile.yml` under ``project_root``."""
    destination = workflow_path or (project_root / DEFAULT_WORKFLOW_RELATIVE)
    if not destination.is_absolute():
        destination = project_root / destination
    if destination.exists() and not force:
        raise FileExistsError(f"Workflow already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    content = render_dockerfile_ssot_workflow(
        dockerfile=dockerfile,
        project_root=".",
        build_tool=build_tool,
    )
    destination.write_text(content, encoding="utf-8")
    return destination
