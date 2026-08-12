#!/bin/sh
set -eu

PLUGIN_FOLDER="{{PLUGIN_FOLDER}}"
PLUGIN_TITLE="{{PLUGIN_TITLE}}"
CONFIG_DIR="${LBPCONFIG:?}/${PLUGIN_FOLDER}"
CONFIG_FILE="${CONFIG_DIR}/smart-home-bridge.ini"
DATA_DIR="${LBPDATA:?}/${PLUGIN_FOLDER}"
LOG_DIR="${LBPLOG:?}/${PLUGIN_FOLDER}"
BIN_DIR="${LBPBIN:?}/${PLUGIN_FOLDER}"
PACKAGE_DIR="${DATA_DIR}/python-package"
VENV_DIR="${DATA_DIR}/venv"
VENV_BIN="${VENV_DIR}/bin"

mkdir -p "$CONFIG_DIR" "$LOG_DIR" "$DATA_DIR" "$BIN_DIR"
touch "$LOG_DIR/smart-home-bridge.log"

if [ ! -f "$PACKAGE_DIR/pyproject.toml" ]; then
    echo "<WARNING> SmartHomeBridge Python package source not found at $PACKAGE_DIR"
    exit 1
fi

python3 -m venv "$VENV_DIR"
"$VENV_BIN/python" -m pip install --upgrade "$PACKAGE_DIR"

for command in \
    smart-home-bridge \
    smart-home-bridge-status \
    smart-home-bridge-config-check \
    smart-home-bridge-door-command \
    smart-home-bridge-sync-mqtt-subscriptions
do
    ln -sf "$VENV_BIN/$command" "$BIN_DIR/$command"
done

if [ -f "$CONFIG_FILE" ]; then
    "$BIN_DIR/smart-home-bridge-sync-mqtt-subscriptions" "$CONFIG_FILE"
fi

echo "<OK> $PLUGIN_TITLE plugin directories prepared"
echo "<OK> SmartHomeBridge shared runtime installed"
