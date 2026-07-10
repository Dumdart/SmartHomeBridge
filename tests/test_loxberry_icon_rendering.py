import importlib.util
import sys
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts/build_loxberry_plugin.py"
SPEC = importlib.util.spec_from_file_location("build_loxberry_plugin", SCRIPT_PATH)
PACKAGER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = PACKAGER
SPEC.loader.exec_module(PACKAGER)
ICON_SVGS = (
    PROJECT_ROOT
    / "deploy/loxberry/plugins/chicken_barn_camera/icons/icon.svg",
    PROJECT_ROOT
    / "deploy/loxberry/plugins/omlet_chicken_door/icons/icon.svg",
)
ICON_PALETTE = (
    PACKAGER.ICON_SURFACE,
    PACKAGER.ICON_BORDER,
    PACKAGER.ICON_GREEN,
    PACKAGER.ICON_CORAL,
)


def _rgba(color: str) -> tuple[int, int, int, int]:
    return (*bytes.fromhex(color.removeprefix("#")), 255)


@pytest.mark.parametrize("icon", ("barn-camera", "omlet-door"))
def test_generated_raster_icons_use_svg_design_system(icon):
    image = Image.open(BytesIO(PACKAGER.create_png_icon(64, icon))).convert("RGBA")
    colors = {color for _, color in image.getcolors(maxcolors=256)}

    assert image.size == (64, 64)
    assert image.getpixel((0, 0))[3] == 0
    assert {_rgba(color) for color in ICON_PALETTE} <= colors


def test_svg_icons_use_packager_palette():
    for icon_path in ICON_SVGS:
        svg = icon_path.read_text(encoding="utf-8")
        assert all(color in svg for color in ICON_PALETTE)
