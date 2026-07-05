import importlib.util
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
    assert "LBPLOG" in script
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
    assert "smart-home-bridge-status" in script
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


def test_loxberry_package_has_plugin_files_at_archive_root(tmp_path):
    build_plugin_archive = load_loxberry_packager().build_plugin_archive

    archive_path = build_plugin_archive(output_path=tmp_path / "smarthomebridge.zip")

    with ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert "plugin.cfg" in names
    assert "postinstall.sh" in names
    assert "bin/bridge_ctl.sh" in names
    assert "webfrontend/htmlauth/index.php" in names
    assert not any(name.startswith("SmartHomeBridge-") for name in names)
    assert not any(name.startswith("deploy/loxberry/") for name in names)
