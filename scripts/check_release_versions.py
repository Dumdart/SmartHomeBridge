from __future__ import annotations

import os
import re
import sys
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
RELEASE_TAG_PATTERN = re.compile(
    r"v(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)"
)


def read_project_version(pyproject_path: Path = PYPROJECT_PATH) -> str:
    with pyproject_path.open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    try:
        version = pyproject["project"]["version"]
    except (KeyError, TypeError) as exc:
        raise ValueError(
            f"Missing project.version in {pyproject_path}"
        ) from exc

    if not isinstance(version, str) or not version:
        raise ValueError(f"Invalid project.version in {pyproject_path}")
    return version


def parse_release_tag(release_tag: str) -> str:
    match = RELEASE_TAG_PATTERN.fullmatch(release_tag)
    if match is None:
        raise ValueError(
            "Invalid release tag "
            f"'{release_tag}'; expected v<major>.<minor>.<patch>"
        )
    return match.group("version")


def check_release_version(
    release_tag: str,
    pyproject_path: Path = PYPROJECT_PATH,
) -> str:
    release_version = parse_release_tag(release_tag)
    project_version = read_project_version(pyproject_path)
    if release_version != project_version:
        raise ValueError(
            f"Release tag version {release_version} does not match "
            f"project version {project_version}"
        )
    return project_version


def main() -> int:
    release_tag = os.environ.get("RELEASE_TAG")
    if not release_tag:
        print("RELEASE_TAG environment variable is required", file=sys.stderr)
        return 1

    try:
        version = check_release_version(release_tag)
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Release tag and pyproject.toml both use version {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
