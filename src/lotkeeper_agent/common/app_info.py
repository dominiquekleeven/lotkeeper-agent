from dataclasses import dataclass
from functools import cache
from pathlib import Path

import tomli


@dataclass
class AppInfo:
    """Application information."""

    name: str
    description: str
    version: str


def find_project_root(start_path: Path = Path(__file__)) -> Path:
    current = start_path.parent
    while current != current.parent:
        if any((current / marker).exists() for marker in ["pyproject.toml", ".env"]):
            return current
        current = current.parent
    raise RuntimeError("Could not find project root")


@cache
def get_app_info() -> AppInfo:
    pyproject_path = find_project_root() / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        pyproject_data = tomli.load(f)

    project_data = pyproject_data["project"]
    app_info_data = {
        "name": project_data["name"],
        "description": project_data["description"],
        "version": project_data["version"],
    }

    return AppInfo(**app_info_data)
