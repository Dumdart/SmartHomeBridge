from pathlib import Path


def test_bridge_ctl_uses_fixed_commands_and_loxberry_paths():
    script = Path("deploy/loxberry/smarthomebridge/bin/bridge_ctl.sh").read_text()

    assert "/opt/loxberry" not in script
    assert "LBPBIN" in script
    assert "LBPCONFIG" in script
    assert "LBHOMEDIR" in script
    assert "LBPLOG" in script
    assert "SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry" in script
    for command in ("start)", "stop)", "restart)", "status)", "dump-config)"):
        assert command in script
    assert "smart-home-bridge-status" in script
    assert "smart-home-bridge-config-check" in script


def test_loxberry_panel_exposes_settings_manual_commands_and_log_tail():
    panel = Path(
        "deploy/loxberry/smarthomebridge/webfrontend/htmlauth/index.php"
    ).read_text()

    assert "save-settings" in panel
    assert "door-command" in panel
    assert "log-tail" in panel
    assert "smart-home-bridge-door-command" in panel
    assert "open_door" in panel
    assert "close_door" in panel
    assert "stop_door" in panel
    assert "get_door_state" in panel
    assert "DOOR_API_KEY" in panel
    assert "CAMERA_HOST" in panel
    assert "CHICKEN_THREAT_ENABLED" in panel
    assert "escapeshellarg($doorCommand)" in panel
