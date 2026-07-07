#!/bin/sh
set -eu

PLUGIN_FOLDER="smarthomebridge"
CONFIG_DIR="${LBPCONFIG:?}/${PLUGIN_FOLDER}"
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
    smart-home-bridge-door-command
do
    ln -sf "$VENV_BIN/$command" "$BIN_DIR/$command"
done

echo "<OK> SmartHomeBridge plugin directories prepared"
echo "<OK> SmartHomeBridge backend installed"
