#!/bin/sh
set -eu

PLUGIN_FOLDER="{{PLUGIN_FOLDER}}"
CONFIG_FILE="${LBPCONFIG:?}/${PLUGIN_FOLDER}/smart-home-bridge.ini"
BACKUP_FILE="/tmp/${PLUGIN_FOLDER}-smart-home-bridge.ini"

if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    echo "<OK> {{PLUGIN_TITLE}} config backed up"
else
    echo "<INFO> No existing {{PLUGIN_TITLE}} config to back up"
fi
