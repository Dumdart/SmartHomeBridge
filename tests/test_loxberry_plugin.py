import importlib.util
import configparser
from pathlib import Path
from zipfile import ZipFile


def load_loxberry_packager():
    script_path = Path("scripts/build_loxberry_plugin.py")
    spec = importlib.util.spec_from_file_location("build_loxberry_plugin", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_bridge_ctl_uses_fixed_commands_and_loxberry_paths():
    script = Path("deploy/loxberry/smarthomebridge/bin/bridge_ctl.sh").read_text()

    assert "/opt/loxberry" not in script
    assert "LBPBIN" in script
    assert "LBPCONFIG" in script
    assert "LBHOMEDIR" in script
    assert "LBPDATA" in script
    assert "LBPLOG" in script
    assert 'VENV_BIN="${LBPDATA}/${PLUGIN_FOLDER}/venv/bin"' in script
    assert 'PLUGIN_FOLDER="${PLUGIN_FOLDER:-smarthomebridge}"' in script
    assert 'BIN_DIR="${LBPBIN}/${PLUGIN_FOLDER}"' in script
    assert 'LOG_DIR="${LBPLOG:-./logs}/${PLUGIN_FOLDER}"' in script
    assert "SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry" in script
    for command in (
        "start)",
        "stop)",
        "restart)",
        "status)",
        "dump-config)",
        "door-command)",
    ):
        assert command in script
    for command in (
        "start-bridge)",
        "stop-bridge)",
        "start-inference)",
        "stop-inference)",
        "install-inference)",
    ):
        assert command not in script
    assert "smart-home-bridge-status" in script
    assert "smart-home-inference" not in script
    assert "smart-home-bridge-config-check" in script
    assert "smart-home-bridge-door-command" in script


def test_loxberry_panel_exposes_settings_manual_commands_and_log_tail():
    panel = Path(
        "deploy/loxberry/smarthomebridge/webfrontend/htmlauth/index.php"
    ).read_text()

    assert "save-settings" in panel
    assert "door-command" in panel
    assert "log-tail" in panel
    assert "$pluginFolder = 'smarthomebridge'" in panel
    assert "$bridgeCtl = $lbpbin . '/' . $pluginFolder . '/bridge_ctl.sh'" in panel
    assert "smart-home-bridge-door-command" not in panel
    assert "open_door" in panel
    assert "close_door" in panel
    assert "stop_door" in panel
    assert "get_door_state" in panel
    assert "DOOR_API_KEY" in panel
    assert "CAMERA_HOST" in panel
    assert "CHICKEN_THREAT_ENABLED" in panel
    assert "CHICKEN_THREAT_INFERENCE_URL" in panel
    assert "start-bridge" not in panel
    assert "stop-bridge" not in panel
    assert "start-inference" not in panel
    assert "stop-inference" not in panel
    assert "install-inference" not in panel
    assert "Inference Install Info" not in panel
    assert "escapeshellcmd($bridgeCtl) . ' door-command '" in panel
    assert "escapeshellarg($doorCommand)" in panel


def test_loxberry_plugin_includes_lifecycle_hooks():
    plugin_dir = Path("deploy/loxberry/smarthomebridge")

    for relative_path in (
        "preinstall.sh",
        "postinstall.sh",
        "preupgrade.sh",
        "postupgrade.sh",
        "uninstall/uninstall",
    ):
        hook = plugin_dir / relative_path
        content = hook.read_text()

        assert hook.exists()
        assert "/opt/loxberry" not in content
        assert "<" in content


def test_loxberry_lifecycle_installs_backend_into_plugin_venv():
    preinstall = Path("deploy/loxberry/smarthomebridge/preinstall.sh").read_text()
    postinstall = Path("deploy/loxberry/smarthomebridge/postinstall.sh").read_text()

    assert "python3 3.11 or newer" in preinstall
    assert "python3 -m venv --help" in preinstall
    assert 'DATA_DIR="${LBPDATA:?}/${PLUGIN_FOLDER}"' in postinstall
    assert 'PACKAGE_DIR="${DATA_DIR}/python-package"' in postinstall
    assert 'VENV_DIR="${DATA_DIR}/venv"' in postinstall
    assert 'python3 -m venv "$VENV_DIR"' in postinstall
    assert '"$VENV_BIN/python" -m pip install --upgrade "$PACKAGE_DIR"' in postinstall
    assert '"$PACKAGE_DIR[inference]"' not in postinstall
    assert "smart-home-inference" not in postinstall
    assert 'ln -sf "$VENV_BIN/$command" "$BIN_DIR/$command"' in postinstall


def test_loxberry_plugin_cfg_declares_interface_in_system_section():
    config = configparser.ConfigParser()
    config.read("deploy/loxberry/smarthomebridge/plugin.cfg")

    assert config["AUTHOR"]["NAME"] == "SmartHomeBridge"
    assert config["AUTHOR"]["EMAIL"]
    assert config["PLUGIN"]["NAME"] == "smarthomebridge"
    assert config["PLUGIN"]["FOLDER"] == "smarthomebridge"
    assert config["PLUGIN"]["TITLE"] == "SmartHomeBridge"
    assert config["PLUGIN"]["VERSION"] == "0.1.0"
    assert config["PLUGIN"]["WEBSITE"] == "https://github.com/Dumdart/SmartHomeBridge"
    assert "INTERFACE" not in config["PLUGIN"]
    assert config["SYSTEM"]["INTERFACE"] == "2.0"
    assert config["SYSTEM"]["LB_MINIMUM"] == "3.0.0"


def test_loxberry_package_has_plugin_files_at_archive_root(tmp_path):
    build_plugin_archive = load_loxberry_packager().build_plugin_archive

    archive_path = build_plugin_archive(output_path=tmp_path / "smarthomebridge.zip")

    with ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert "plugin.cfg" in names
    assert "postinstall.sh" in names
    assert "bin/bridge_ctl.sh" in names
    assert "icons/icon.svg" in names
    assert "icons/icon_64.png" in names
    assert "icons/icon_128.png" in names
    assert "icons/icon_256.png" in names
    assert "icons/icon_512.png" in names
    assert "webfrontend/htmlauth/index.php" in names
    assert "data/python-package/pyproject.toml" in names
    assert "data/python-package/README.MD" in names
    assert "data/python-package/src/smart_home_bridge/__main__.py" in names
    assert "data/python-package/src/smart_home_bridge/config.py" in names
    assert (
        "data/python-package/src/smart_home_inference/models/chicken_thread/model/chicken_threat_detector_best_v3.pt"
        in names
    )
    assert not any(name.startswith("SmartHomeBridge-") for name in names)
    assert not any(name.startswith("deploy/loxberry/") for name in names)
