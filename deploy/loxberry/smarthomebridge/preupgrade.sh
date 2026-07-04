#!/bin/sh
set -eu

PLUGIN_FOLDER="smarthomebridge"
CONFIG_FILE="${LBPCONFIG:?}/${PLUGIN_FOLDER}/smart-home-bridge.ini"
BACKUP_FILE="/tmp/smarthomebridge-smart-home-bridge.ini"

if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    echo "<OK> SmartHomeBridge config backed up"
else
    echo "<INFO> No existing SmartHomeBridge config to back up"
fi
