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
