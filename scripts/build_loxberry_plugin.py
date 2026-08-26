from __future__ import annotations

import argparse
import configparser
import io
import json
import stat
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOXBERRY_ROOT = PROJECT_ROOT / "deploy" / "loxberry"
SHARED_SOURCE_DIR = LOXBERRY_ROOT / "shared"
PLUGINS_SOURCE_DIR = LOXBERRY_ROOT / "plugins"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "build" / "loxberry"
PNG_ICON_SIZES = (64, 128, 256, 512)
ICON_SURFACE = "#f8f4ec"
ICON_BORDER = "#dce7df"
ICON_GREEN = "#195b43"
ICON_CORAL = "#e36b68"
PYTHON_PACKAGE_ROOT = "data/python-package"
PYTHON_PACKAGE_FILES = (
    PROJECT_ROOT / "pyproject.toml",
    PROJECT_ROOT / "README.MD",
    PROJECT_ROOT / "requirements-loxberry.txt",
)
PYTHON_PACKAGE_SOURCE_DIRS = (
    PROJECT_ROOT / "src" / "smart_home_bridge",
    PROJECT_ROOT / "src" / "smart_home_contracts",
)
MANIFEST_NAME = "plugin.json"


@dataclass(frozen=True)
class LoxberryPlugin:
    plugin_id: str
    name: str
    folder: str
    title: str
    device_keys: tuple[str, ...]
    icon: str
    archive_name: str
    source_dir: Path

    @property
    def replacements(self) -> dict[bytes, bytes]:
        values = {
            "PLUGIN_FOLDER": self.folder,
            "PLUGIN_TITLE": self.title,
            "DEVICE_KEYS": ",".join(self.device_keys),
        }
        return {
            f"{{{{{key}}}}}".encode(): value.encode()
            for key, value in values.items()
        }


def discover_plugins(
    source_dir: Path = PLUGINS_SOURCE_DIR,
) -> dict[str, LoxberryPlugin]:
    plugins: dict[str, LoxberryPlugin] = {}
    if not source_dir.is_dir():
        raise FileNotFoundError(f"LoxBerry plugin directory not found: {source_dir}")

    for manifest_path in sorted(source_dir.glob(f"*/{MANIFEST_NAME}")):
        values = json.loads(manifest_path.read_text(encoding="utf-8"))
        plugin = LoxberryPlugin(
            plugin_id=_required_manifest_string(values, "id", manifest_path),
            name=_required_manifest_string(values, "name", manifest_path),
            folder=_required_manifest_string(values, "folder", manifest_path),
            title=_required_manifest_string(values, "title", manifest_path),
            device_keys=tuple(values.get("device_keys", ())),
            icon=_required_manifest_string(values, "icon", manifest_path),
            archive_name=_required_manifest_string(
                values,
                "archive_name",
                manifest_path,
            ),
            source_dir=manifest_path.parent,
        )
        if not plugin.device_keys or not all(
            isinstance(key, str) and key for key in plugin.device_keys
        ):
            raise ValueError(f"Invalid device_keys in {manifest_path}")
        if plugin.icon not in {"omlet-door", "barn-camera"}:
            raise ValueError(f"Unsupported icon '{plugin.icon}' in {manifest_path}")
        if plugin.plugin_id in plugins:
            raise ValueError(f"Duplicate LoxBerry plugin id: {plugin.plugin_id}")
        _validate_plugin_config(plugin)
        plugins[plugin.plugin_id] = plugin

    if not plugins:
        raise ValueError(f"No LoxBerry plugin manifests found in {source_dir}")
    return plugins


def _required_manifest_string(
    values: dict,
    key: str,
    manifest_path: Path,
) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid {key} in {manifest_path}")
    return value.strip()


def _validate_plugin_config(plugin: LoxberryPlugin) -> None:
    config_path = plugin.source_dir / "plugin.cfg"
    if not config_path.is_file():
        raise FileNotFoundError(f"plugin.cfg not found for {plugin.plugin_id}")

    config = configparser.ConfigParser()
    config.read(config_path)
    if config.get("PLUGIN", "NAME", fallback="") != plugin.folder:
        raise ValueError(
            f"PLUGIN.NAME in {config_path} must match manifest folder {plugin.folder}"
        )
    if config.get("PLUGIN", "FOLDER", fallback="") != plugin.folder:
        raise ValueError(
            f"PLUGIN.FOLDER in {config_path} must match manifest folder {plugin.folder}"
        )
    if config.get("PLUGIN", "TITLE", fallback="") != plugin.title:
        raise ValueError(
            f"PLUGIN.TITLE in {config_path} must match manifest title {plugin.title}"
        )


def create_png_icon(size: int, icon: str = "omlet-door") -> bytes:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale = size / 64

    def point(value: float) -> int:
        return round(value * scale)

    draw.rounded_rectangle(
        (point(1), point(1), size - point(1), size - point(1)),
        radius=point(12),
        fill=ICON_SURFACE,
        outline=ICON_BORDER,
        width=max(1, point(2)),
    )
    if icon == "omlet-door":
        _draw_omlet_door_icon(draw, point)
    elif icon == "barn-camera":
        _draw_barn_camera_icon(draw, point)
    else:
        raise ValueError(f"Unsupported plugin icon: {icon}")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _draw_omlet_door_icon(draw: ImageDraw.ImageDraw, point) -> None:
    stroke = max(1, point(3))
    draw.line(
        [(point(9), point(49)), (point(45), point(49))],
        fill=ICON_GREEN,
        width=stroke,
    )
    draw.line(
        [
            (point(14), point(49)),
            (point(14), point(14)),
            (point(40), point(14)),
            (point(40), point(49)),
        ],
        fill=ICON_GREEN,
        width=stroke,
        joint="curve",
    )
    draw.line(
        [(point(34), point(14)), (point(34), point(49))],
        fill=ICON_GREEN,
        width=stroke,
    )
    draw.polygon(
        [
            (point(55), point(35)),
            (point(60), point(38)),
            (point(55), point(40)),
        ],
        fill=ICON_CORAL,
    )
    draw.ellipse(
        (point(47), point(30), point(58), point(41)),
        fill=ICON_SURFACE,
        outline=ICON_CORAL,
        width=stroke,
    )
    draw.polygon(
        [
            (point(51), point(39)),
            (point(57), point(43)),
            (point(53), point(49)),
            (point(47), point(52)),
            (point(36), point(52)),
            (point(45), point(41)),
        ],
        fill=ICON_SURFACE,
        outline=ICON_CORAL,
        width=stroke,
    )
    draw.line(
        [
            (point(46), point(43)),
            (point(38), point(52)),
            (point(49), point(52)),
        ],
        fill=ICON_CORAL,
        width=stroke,
        joint="curve",
    )
    draw.ellipse(
        (point(52), point(34), point(54), point(36)),
        fill=ICON_CORAL,
    )


def _draw_barn_camera_icon(draw: ImageDraw.ImageDraw, point) -> None:
    stroke = max(1, point(3))
    draw.line(
        [(point(6), point(22)), (point(38), point(15))],
        fill=ICON_CORAL,
        width=stroke,
    )
    draw.line(
        [
            (point(9), point(22)),
            (point(9), point(38)),
            (point(38), point(38)),
            (point(38), point(16)),
        ],
        fill=ICON_CORAL,
        width=stroke,
        joint="curve",
    )
    draw.rectangle(
        (point(14), point(28), point(30), point(38)),
        outline=ICON_CORAL,
        width=stroke,
    )
    draw.line(
        [(point(14), point(33)), (point(30), point(33))],
        fill=ICON_CORAL,
        width=stroke,
    )
    draw.polygon(
        [
            (point(32), point(29)),
            (point(36), point(24)),
            (point(46), point(24)),
            (point(50), point(29)),
        ],
        fill=ICON_GREEN,
    )
    draw.rounded_rectangle(
        (point(27), point(28), point(58), point(53)),
        radius=point(4),
        fill=ICON_SURFACE,
        outline=ICON_GREEN,
        width=stroke,
    )
    draw.ellipse(
        (point(36), point(35), point(49), point(48)),
        fill=ICON_GREEN,
    )
    draw.ellipse(
        (point(40), point(39), point(45), point(44)),
        fill=ICON_CORAL,
    )


def should_include_python_source(path: Path) -> bool:
    parts = set(path.parts)
    if "__pycache__" in parts or "notes" in parts:
        return False
    if path.suffix in {".pyc", ".pyo"}:
        return False
    return path.is_file()


def build_plugin_archive(
    plugin: str | LoxberryPlugin,
    output_path: Path | None = None,
    *,
    plugins: dict[str, LoxberryPlugin] | None = None,
    shared_source_dir: Path = SHARED_SOURCE_DIR,
) -> Path:
    plugin_catalog = plugins or discover_plugins()
    selected = plugin_catalog[plugin] if isinstance(plugin, str) else plugin
    destination = (
        output_path or DEFAULT_OUTPUT_DIR / selected.archive_name
    ).resolve()

    archive_files = _collect_archive_files(shared_source_dir, selected.source_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for archive_path, path in sorted(archive_files.items()):
            data = _render_file(path, selected.replacements)
            info = ZipInfo.from_file(path, archive_path)
            permissions = stat.S_IMODE(path.stat().st_mode)
            if path.suffix == ".sh" or archive_path == "uninstall/uninstall":
                permissions |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            info.external_attr = permissions << 16
            archive.writestr(info, data, compress_type=ZIP_DEFLATED)

        for size in PNG_ICON_SIZES:
            archive.writestr(
                f"icons/icon_{size}.png",
                create_png_icon(size, selected.icon),
                compress_type=ZIP_DEFLATED,
            )

        for path in PYTHON_PACKAGE_FILES:
            archive.write(path, f"{PYTHON_PACKAGE_ROOT}/{path.name}")

        for package_src in PYTHON_PACKAGE_SOURCE_DIRS:
            for path in sorted(package_src.rglob("*")):
                if not should_include_python_source(path):
                    continue
                relative_path = path.relative_to(PROJECT_ROOT).as_posix()
                archive.write(path, f"{PYTHON_PACKAGE_ROOT}/{relative_path}")

    return destination


def _collect_archive_files(shared_dir: Path, plugin_dir: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for source_dir in (shared_dir, plugin_dir):
        if not source_dir.is_dir():
            raise FileNotFoundError(f"LoxBerry source directory not found: {source_dir}")
        for path in source_dir.rglob("*"):
            if path.is_file() and path.name != MANIFEST_NAME:
                files[path.relative_to(source_dir).as_posix()] = path
    return files


def _render_file(path: Path, replacements: dict[bytes, bytes]) -> bytes:
    content = path.read_bytes()
    if path.suffix == ".sh" or path.as_posix().endswith("uninstall/uninstall"):
        content = content.replace(b"\r\n", b"\n")
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    if b"{{" in content or b"}}" in content:
        raise ValueError(f"Unresolved template placeholder in {path}")
    return content


def build_selected_plugins(
    plugin_ids: Iterable[str] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, ...]:
    plugins = discover_plugins()
    selected_ids = tuple(plugin_ids) if plugin_ids is not None else tuple(plugins)
    unknown = sorted(set(selected_ids) - set(plugins))
    if unknown:
        raise ValueError(f"Unknown LoxBerry plugin ids: {', '.join(unknown)}")
    return tuple(
        build_plugin_archive(
            plugin_id,
            output_dir / plugins[plugin_id].archive_name,
            plugins=plugins,
        )
        for plugin_id in selected_ids
    )


def parse_args() -> argparse.Namespace:
    plugins = discover_plugins()
    parser = argparse.ArgumentParser(
        description="Build one or more modular LoxBerry plugin ZIPs."
    )
    parser.add_argument(
        "--plugin",
        action="append",
        choices=tuple(plugins),
        help="Plugin id to build. Repeat to select multiple; defaults to all.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory. Defaults to {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List plugin ids and display names without building.",
    )
    args = parser.parse_args()
    args.plugins = plugins
    return args


def main() -> None:
    args = parse_args()
    if args.list:
        for plugin in args.plugins.values():
            print(f"{plugin.plugin_id}\t{plugin.name}")
        return

    for output_path in build_selected_plugins(args.plugin, args.output_dir):
        print(output_path)


if __name__ == "__main__":
    main()
