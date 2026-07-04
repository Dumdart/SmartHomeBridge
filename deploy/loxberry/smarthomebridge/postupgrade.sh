#!/bin/sh
set -eu

PLUGIN_FOLDER="smarthomebridge"
CONFIG_DIR="${LBPCONFIG:?}/${PLUGIN_FOLDER}"
CONFIG_FILE="${CONFIG_DIR}/smart-home-bridge.ini"
BACKUP_FILE="/tmp/smarthomebridge-smart-home-bridge.ini"

mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_FILE" ] && [ -f "$BACKUP_FILE" ]; then
    cp "$BACKUP_FILE" "$CONFIG_FILE"
    echo "<OK> SmartHomeBridge config restored"
else
    echo "<INFO> SmartHomeBridge config restore not required"
fi
