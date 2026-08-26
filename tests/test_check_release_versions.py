from pathlib import Path

import pytest

from scripts.check_release_versions import (
    check_release_version,
    parse_release_tag,
    read_project_version,
)


def write_pyproject(path: Path, version: str) -> Path:
    pyproject_path = path / "pyproject.toml"
    pyproject_path.write_text(
        f'[project]\nname = "example"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    return pyproject_path


def test_release_tag_matches_project_version(tmp_path):
    pyproject_path = write_pyproject(tmp_path, "1.2.3")

    assert check_release_version("v1.2.3", pyproject_path) == "1.2.3"


def test_release_tag_must_match_project_version(tmp_path):
    pyproject_path = write_pyproject(tmp_path, "1.2.3")

    with pytest.raises(ValueError, match="does not match project version 1.2.3"):
        check_release_version("v1.2.4", pyproject_path)


@pytest.mark.parametrize("release_tag", ["1.2.3", "v1.2", "v01.2.3", "v1.2.x"])
def test_release_tag_must_have_valid_format(release_tag):
    with pytest.raises(ValueError, match="Invalid release tag"):
        parse_release_tag(release_tag)


def test_project_version_is_required(tmp_path):
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text('[project]\nname = "example"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="Missing project.version"):
        read_project_version(pyproject_path)
