from __future__ import annotations

import argparse
import stat
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SOURCE_DIR = PROJECT_ROOT / "deploy" / "loxberry" / "smarthomebridge"
DEFAULT_OUTPUT = PROJECT_ROOT / "build" / "smarthomebridge-loxberry.zip"


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
