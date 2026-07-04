#!/bin/sh
set -eu

PLUGIN_FOLDER="smarthomebridge"
CONFIG_DIR="${LBPCONFIG:?}/${PLUGIN_FOLDER}"
LOG_DIR="${LBPLOG:?}/${PLUGIN_FOLDER}"

mkdir -p "$CONFIG_DIR" "$LOG_DIR"
touch "$LOG_DIR/smart-home-bridge.log"

echo "<OK> SmartHomeBridge plugin directories prepared"
