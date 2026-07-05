from __future__ import annotations

import argparse
import io
import stat
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SOURCE_DIR = PROJECT_ROOT / "deploy" / "loxberry" / "smarthomebridge"
DEFAULT_OUTPUT = PROJECT_ROOT / "build" / "smarthomebridge-loxberry.zip"
PNG_ICON_SIZES = (64, 128, 256, 512)


def create_png_icon(size: int) -> bytes:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale = size / 64

    def point(value: float) -> int:
        return round(value * scale)

    draw.rounded_rectangle(
        (0, 0, size - 1, size - 1),
        radius=point(8),
        fill="#1f2937",
    )
    draw.rectangle(
        (point(14), point(36), point(50), point(52)),
        fill="#f9fafb",
    )
    draw.line(
        [
            (point(10), point(36)),
            (point(32), point(16)),
            (point(54), point(36)),
        ],
        fill="#f59e0b",
        width=max(1, point(5)),
        joint="curve",
    )
    draw.rectangle(
        (point(25), point(38), point(39), point(52)),
        fill="#374151",
    )
    draw.ellipse(
        (point(41), point(11), point(53), point(23)),
        fill="#22c55e",
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_plugin_archive(
    source_dir: Path = PLUGIN_SOURCE_DIR,
    output_path: Path = DEFAULT_OUTPUT,
) -> Path:
    source_dir = source_dir.resolve()
    output_path = output_path.resolve()

    if not (source_dir / "plugin.cfg").is_file():
        raise FileNotFoundError(f"plugin.cfg not found in {source_dir}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue

            archive_path = path.relative_to(source_dir).as_posix()
            info = ZipInfo.from_file(path, archive_path)
            permissions = stat.S_IMODE(path.stat().st_mode)
            if path.suffix == ".sh" or archive_path == "uninstall/uninstall":
                permissions |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            info.external_attr = permissions << 16

            with path.open("rb") as source_file:
                archive.writestr(info, source_file.read(), compress_type=ZIP_DEFLATED)

        for size in PNG_ICON_SIZES:
            archive.writestr(
                f"icons/icon_{size}.png",
                create_png_icon(size),
                compress_type=ZIP_DEFLATED,
            )

    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a LoxBerry plugin ZIP with plugin.cfg at archive root."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output ZIP path. Defaults to {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = build_plugin_archive(output_path=args.output)
    print(output_path)


if __name__ == "__main__":
    main()
