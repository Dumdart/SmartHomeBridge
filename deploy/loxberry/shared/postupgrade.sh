#!/bin/sh
set -eu

PLUGIN_FOLDER="{{PLUGIN_FOLDER}}"
CONFIG_DIR="${LBPCONFIG:?}/${PLUGIN_FOLDER}"
CONFIG_FILE="${CONFIG_DIR}/smart-home-bridge.ini"
BACKUP_FILE="/tmp/${PLUGIN_FOLDER}-smart-home-bridge.ini"

mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_FILE" ] && [ -f "$BACKUP_FILE" ]; then
    cp "$BACKUP_FILE" "$CONFIG_FILE"
    echo "<OK> {{PLUGIN_TITLE}} config restored"
else
    echo "<INFO> {{PLUGIN_TITLE}} config restore not required"
fi
