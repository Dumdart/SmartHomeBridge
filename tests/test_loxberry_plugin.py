from pathlib import Path


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
