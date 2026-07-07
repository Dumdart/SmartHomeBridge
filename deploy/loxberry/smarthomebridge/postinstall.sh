#!/bin/sh
set -eu

PLUGIN_FOLDER="smarthomebridge"
CONFIG_DIR="${LBPCONFIG:?}/${PLUGIN_FOLDER}"
DATA_DIR="${LBPDATA:?}/${PLUGIN_FOLDER}"
LOG_DIR="${LBPLOG:?}/${PLUGIN_FOLDER}"
BIN_DIR="${LBPBIN:?}/${PLUGIN_FOLDER}"
PACKAGE_DIR="${DATA_DIR}/python-package"
VENV_DIR="${DATA_DIR}/venv"
INFERENCE_VENV_DIR="${DATA_DIR}/inference-venv"
VENV_BIN="${VENV_DIR}/bin"
INFERENCE_VENV_BIN="${INFERENCE_VENV_DIR}/bin"

mkdir -p "$CONFIG_DIR" "$LOG_DIR" "$DATA_DIR" "$BIN_DIR"
touch "$LOG_DIR/smart-home-bridge.log"

if [ ! -f "$PACKAGE_DIR/pyproject.toml" ]; then
    echo "<WARNING> SmartHomeBridge Python package source not found at $PACKAGE_DIR"
    exit 1
fi

python3 -m venv "$VENV_DIR"
"$VENV_BIN/python" -m pip install --upgrade "$PACKAGE_DIR"
python3 -m venv "$INFERENCE_VENV_DIR"
"$INFERENCE_VENV_BIN/python" -m pip install --upgrade "$PACKAGE_DIR[inference]"

for command in \
    smart-home-bridge \
    smart-home-bridge-status \
    smart-home-bridge-config-check \
    smart-home-bridge-door-command \
    smart-home-inference
do
    if [ "$command" = "smart-home-inference" ]; then
        ln -sf "$INFERENCE_VENV_BIN/$command" "$BIN_DIR/$command"
    else
        ln -sf "$VENV_BIN/$command" "$BIN_DIR/$command"
    fi
done

echo "<OK> SmartHomeBridge plugin directories prepared"
echo "<OK> SmartHomeBridge backend installed"
echo "<OK> SmartHomeBridge inference backend installed"
