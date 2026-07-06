import tomllib
from pathlib import Path


def test_gui_entrypoint_is_packaged_as_gui_script():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())

    assert pyproject["project"]["gui-scripts"]["smart-home-bridge-gui"] == (
        "smart_home_bridge.gui:run"
    )
    assert "smart-home-bridge-gui" not in pyproject["project"]["scripts"]
