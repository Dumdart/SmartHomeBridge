#!/bin/sh
set -eu

PLUGIN_FOLDER="{{PLUGIN_FOLDER}}"
CONFIG_DIR="${LBPCONFIG:?}/${PLUGIN_FOLDER}"
CONFIG_FILE="${CONFIG_DIR}/smart-home-bridge.ini"
BACKUP_FILE="/tmp/${PLUGIN_FOLDER}-smart-home-bridge.ini"
RUNNING_FILE="/tmp/${PLUGIN_FOLDER}-smart-home-bridge-was-running"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BRIDGE_CTL="${LBPBIN:?}/${PLUGIN_FOLDER}/bridge_ctl.sh"
RESTART_AFTER_UPGRADE=false

mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_FILE" ] && [ -f "$BACKUP_FILE" ]; then
    cp "$BACKUP_FILE" "$CONFIG_FILE"
    echo "<OK> {{PLUGIN_TITLE}} config restored"
else
    echo "<INFO> {{PLUGIN_TITLE}} config restore not required"
fi

# Check upgrades from older releases may leave the old bridge process running.
if [ -f "$RUNNING_FILE" ]; then
    RESTART_AFTER_UPGRADE=true
elif [ -x "$BRIDGE_CTL" ] && "$BRIDGE_CTL" is-running >/dev/null 2>&1; then
    RESTART_AFTER_UPGRADE=true
    "$BRIDGE_CTL" stop
fi

# Check that upgrades install the bundled application code just like fresh installs.
sh "${SCRIPT_DIR}/postinstall.sh"

if [ "$RESTART_AFTER_UPGRADE" = true ]; then
    "$BRIDGE_CTL" start
    rm -f "$RUNNING_FILE"
    echo "<OK> {{PLUGIN_TITLE}} restarted after upgrade"
fi
