import configparser
import importlib.util
import sys
from pathlib import Path
from zipfile import ZipFile


def load_loxberry_packager():
    script_path = Path("scripts/build_loxberry_plugin.py")
    spec = importlib.util.spec_from_file_location("build_loxberry_plugin", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def archive_contents(path: Path) -> tuple[set[str], dict[str, str]]:
    with ZipFile(path) as archive:
        names = set(archive.namelist())
        text = {
            name: archive.read(name).decode()
            for name in names
            if name.endswith((".cfg", ".ini", ".php", ".sh"))
            or name == "uninstall/uninstall"
        }
    return names, text


def test_plugin_catalog_declares_independent_device_plugins():
    plugins = load_loxberry_packager().discover_plugins()

    assert set(plugins) == {"omlet-chicken-door", "chicken-barn-camera"}
    assert plugins["omlet-chicken-door"].name == "OmletChickenDoorPlugin"
    assert plugins["omlet-chicken-door"].folder == "omletchickendoor"
    assert plugins["omlet-chicken-door"].device_keys == ("chicken_door",)
    assert plugins["omlet-chicken-door"].icon == "omlet-door"
    assert plugins["chicken-barn-camera"].name == "ChickenBarnCameraPlugin"
    assert plugins["chicken-barn-camera"].folder == "chickenbarncamera"
    assert plugins["chicken-barn-camera"].device_keys == (
        "chicken_thread_detector",
    )
    assert plugins["chicken-barn-camera"].icon == "barn-camera"


def test_build_selected_plugins_builds_only_requested_archive(tmp_path):
    packager = load_loxberry_packager()

    paths = packager.build_selected_plugins(["omlet-chicken-door"], tmp_path)

    assert paths == ((tmp_path / "omlet-chicken-door-loxberry.zip").resolve(),)
    assert paths[0].is_file()
    assert not (tmp_path / "chicken-barn-camera-loxberry.zip").exists()


def test_each_archive_combines_shared_runtime_with_device_profile(tmp_path):
    packager = load_loxberry_packager()

    paths = packager.build_selected_plugins(output_dir=tmp_path)

    assert {path.name for path in paths} == {
        "omlet-chicken-door-loxberry.zip",
        "chicken-barn-camera-loxberry.zip",
    }
    expected_shared_files = {
        "plugin.cfg",
        "preinstall.sh",
        "postinstall.sh",
        "preupgrade.sh",
        "postupgrade.sh",
        "uninstall/uninstall",
        "bin/bridge_ctl.sh",
        "icons/icon.svg",
        "icons/icon_64.png",
        "icons/icon_128.png",
        "icons/icon_256.png",
        "icons/icon_512.png",
        "webfrontend/htmlauth/index.php",
        "webfrontend/htmlauth/plugin.php",
        "config/smart-home-bridge.ini",
        "mqtt_subscriptions.cfg",
        "data/python-package/pyproject.toml",
        "data/python-package/README.MD",
        "data/python-package/src/smart_home_bridge/__main__.py",
        "data/python-package/src/smart_home_contracts/chicken_thread/Detection.py",
    }
    for path in paths:
        names, text = archive_contents(path)
        assert expected_shared_files <= names
        assert "plugin.json" not in names
        assert not any("{{" in value or "}}" in value for value in text.values())
        assert not any(name.startswith("deploy/loxberry/") for name in names)
        assert not any(name.startswith("data/python-package/src/smart_home_inference/") for name in names)


def test_omlet_plugin_contains_only_door_configuration(tmp_path):
    packager = load_loxberry_packager()
    archive_path = packager.build_plugin_archive(
        "omlet-chicken-door",
        tmp_path / "door.zip",
    )
    _, text = archive_contents(archive_path)

    plugin_config = configparser.ConfigParser()
    plugin_config.read_string(text["plugin.cfg"])
    assert plugin_config["PLUGIN"]["FOLDER"] == "omletchickendoor"
    assert plugin_config["PLUGIN"]["TITLE"] == "OmletChickenDoorPlugin"
    assert plugin_config["SYSTEM"]["INTERFACE"] == "2.0"
    assert "BRIDGE_DEVICES_ENABLED=chicken_door" in text[
        "config/smart-home-bridge.ini"
    ]
    assert "DOOR_API_KEY=" in text["config/smart-home-bridge.ini"]
    assert "CAMERA_HOST=" not in text["config/smart-home-bridge.ini"]
    assert "open_door" in text["webfrontend/htmlauth/plugin.php"]
    assert 'PLUGIN_FOLDER="${PLUGIN_FOLDER:-omletchickendoor}"' in text[
        "bin/bridge_ctl.sh"
    ]
    assert 'ENABLED_DEVICES="chicken_door"' in text["bin/bridge_ctl.sh"]


def test_camera_plugin_contains_only_camera_configuration(tmp_path):
    packager = load_loxberry_packager()
    archive_path = packager.build_plugin_archive(
        "chicken-barn-camera",
        tmp_path / "camera.zip",
    )
    _, text = archive_contents(archive_path)

    plugin_config = configparser.ConfigParser()
    plugin_config.read_string(text["plugin.cfg"])
    assert plugin_config["PLUGIN"]["FOLDER"] == "chickenbarncamera"
    assert plugin_config["PLUGIN"]["TITLE"] == "ChickenBarnCameraPlugin"
    assert "BRIDGE_DEVICES_ENABLED=chicken_thread_detector" in text[
        "config/smart-home-bridge.ini"
    ]
    assert "CAMERA_HOST=" in text["config/smart-home-bridge.ini"]
    assert "CHICKEN_THREAT_ENABLED=true" in text[
        "config/smart-home-bridge.ini"
    ]
    assert "DOOR_API_KEY=" not in text["config/smart-home-bridge.ini"]
    assert "$allowedDoorCommands = array();" in text[
        "webfrontend/htmlauth/plugin.php"
    ]
    assert 'PLUGIN_FOLDER="${PLUGIN_FOLDER:-chickenbarncamera}"' in text[
        "bin/bridge_ctl.sh"
    ]
    assert 'ENABLED_DEVICES="chicken_thread_detector"' in text[
        "bin/bridge_ctl.sh"
    ]


def test_shared_lifecycle_installs_runtime_in_plugin_specific_paths(tmp_path):
    packager = load_loxberry_packager()
    archive_path = packager.build_plugin_archive(
        "chicken-barn-camera",
        tmp_path / "camera.zip",
    )
    _, text = archive_contents(archive_path)
    preinstall = text["preinstall.sh"]
    postinstall = text["postinstall.sh"]
    bridge_ctl = text["bin/bridge_ctl.sh"]

    assert "python3 3.11 or newer" in preinstall
    assert "python3 -m venv --help" in preinstall
    assert 'PLUGIN_FOLDER="chickenbarncamera"' in postinstall
    assert 'DATA_DIR="${LBPDATA:?}/${PLUGIN_FOLDER}"' in postinstall
    assert 'PACKAGE_DIR="${DATA_DIR}/python-package"' in postinstall
    assert 'VENV_DIR="${DATA_DIR}/venv"' in postinstall
    assert 'python3 -m venv "$VENV_DIR"' in postinstall
    assert '"$VENV_BIN/python" -m pip install --upgrade "$PACKAGE_DIR"' in postinstall
    assert "SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry" in bridge_ctl
    assert "export PLUGIN_FOLDER" in bridge_ctl
    assert "Door commands are not supported by $PLUGIN_TITLE" in bridge_ctl


def test_shared_web_panel_preserves_fixed_device_profile():
    panel = Path("deploy/loxberry/shared/webfrontend/htmlauth/index.php").read_text()

    assert "require __DIR__ . '/plugin.php'" in panel
    assert "save-settings" in panel
    assert "door-command" in panel
    assert "log-tail" in panel
    assert "array_merge($fixedSettings, $settings)" in panel
    assert "escapeshellarg($argument)" in panel
    assert "count($allowedDoorCommands) > 0" in panel


def test_shared_web_panel_uses_native_loxberry_ui_and_safe_form_flow():
    panel = Path("deploy/loxberry/shared/webfrontend/htmlauth/index.php").read_text()

    assert "require_once 'loxberry_web.php'" in panel
    assert "LBWeb::lbheader" in panel
    assert "LBWeb::lbfooter" in panel
    assert "header('Location: '" in panel
    assert "hash_equals($csrfToken" in panel
    assert "Leave blank to keep the existing value" in panel
    assert "redact_output" in panel
    assert "confirm('Close the chicken door now?" in panel


def test_plugin_profiles_define_human_friendly_field_schemas():
    camera = Path(
        "deploy/loxberry/plugins/chicken_barn_camera/webfrontend/htmlauth/plugin.php"
    ).read_text()
    door = Path(
        "deploy/loxberry/plugins/omlet_chicken_door/webfrontend/htmlauth/plugin.php"
    ).read_text()

    assert "$fieldSchema = array(" in camera
    assert "'label' => 'Camera address'" in camera
    assert "'sensitive' => true" in camera
    assert "'test-camera' => 'Test camera'" in camera
    assert "$fieldSchema = array(" in door
    assert "'label' => 'Omlet API key'" in door
    assert "'test-door' => 'Test API & device'" in door
    assert "array('open_door', 'close_door', 'stop_door', 'get_door_state')" in door


def test_archives_mark_lifecycle_and_control_scripts_executable(tmp_path):
    packager = load_loxberry_packager()
    archive_path = packager.build_plugin_archive(
        "omlet-chicken-door",
        tmp_path / "door.zip",
    )

    with ZipFile(archive_path) as archive:
        for name in (
            "preinstall.sh",
            "postinstall.sh",
            "preupgrade.sh",
            "postupgrade.sh",
            "uninstall/uninstall",
            "bin/bridge_ctl.sh",
        ):
            mode = archive.getinfo(name).external_attr >> 16
            assert mode & 0o111


def test_plugins_have_distinct_vector_and_generated_raster_icons(tmp_path):
    packager = load_loxberry_packager()
    door_archive = packager.build_plugin_archive(
        "omlet-chicken-door",
        tmp_path / "door.zip",
    )
    camera_archive = packager.build_plugin_archive(
        "chicken-barn-camera",
        tmp_path / "camera.zip",
    )

    with ZipFile(door_archive) as archive:
        door_svg = archive.read("icons/icon.svg").decode()
        door_png = archive.read("icons/icon_256.png")
    with ZipFile(camera_archive) as archive:
        camera_svg = archive.read("icons/icon.svg").decode()
        camera_png = archive.read("icons/icon_256.png")

    assert 'aria-label="Omlet chicken door"' in door_svg
    assert 'aria-label="Chicken barn camera"' in camera_svg
    assert door_svg != camera_svg
    assert door_png != camera_png
