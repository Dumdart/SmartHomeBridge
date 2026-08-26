#!/bin/sh
set -eu

PLUGIN_FOLDER="{{PLUGIN_FOLDER}}"
CONFIG_FILE="${LBPCONFIG:?}/${PLUGIN_FOLDER}/smart-home-bridge.ini"
BACKUP_FILE="/tmp/${PLUGIN_FOLDER}-smart-home-bridge.ini"
RUNNING_FILE="/tmp/${PLUGIN_FOLDER}-smart-home-bridge-was-running"
BRIDGE_CTL="${LBPBIN:?}/${PLUGIN_FOLDER}/bridge_ctl.sh"

rm -f "$RUNNING_FILE"
if [ -x "$BRIDGE_CTL" ] && "$BRIDGE_CTL" is-running >/dev/null 2>&1; then
    touch "$RUNNING_FILE"
    "$BRIDGE_CTL" stop
fi

if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    echo "<OK> {{PLUGIN_TITLE}} config backed up"
else
    echo "<INFO> No existing {{PLUGIN_TITLE}} config to back up"
fi
