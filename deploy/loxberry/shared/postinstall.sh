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
BUILD_REQUIREMENTS_FILE="${PACKAGE_DIR}/requirements-loxberry-build.txt"
REQUIREMENTS_FILE="${PACKAGE_DIR}/requirements-loxberry.txt"
VENV_DIR="${DATA_DIR}/venv"
VENV_BIN="${VENV_DIR}/bin"
VENV_CANDIDATE=""
VENV_LINK=""
VENV_PREVIOUS_LINK="${DATA_DIR}/venv.previous"
ACTIVATED=false

cleanup_candidate() {
    if [ -n "$VENV_LINK" ]; then
        rm -f "$VENV_LINK"
    fi
    if [ "$ACTIVATED" = false ] && [ -n "$VENV_CANDIDATE" ]; then
        rm -rf "$VENV_CANDIDATE"
    fi
}

cleanup_previous_runtime() {
    if [ ! -L "$VENV_PREVIOUS_LINK" ]; then
        return
    fi

    stale_runtime="$(readlink -f "$VENV_PREVIOUS_LINK" 2>/dev/null || true)"
    current_runtime="$(readlink -f "$VENV_DIR" 2>/dev/null || true)"
    case "$stale_runtime" in
        "${DATA_DIR}"/.venv-runtime-*|"${DATA_DIR}"/.venv-legacy-*)
            if [ "$stale_runtime" != "$current_runtime" ]; then
                rm -rf "$stale_runtime"
            fi
            ;;
    esac
    rm -f "$VENV_PREVIOUS_LINK"
}

trap cleanup_candidate EXIT HUP INT TERM

mkdir -p "$CONFIG_DIR" "$LOG_DIR" "$DATA_DIR" "$BIN_DIR"
touch "$LOG_DIR/smart-home-bridge.log"

if [ ! -f "$PACKAGE_DIR/pyproject.toml" ]; then
    echo "<WARNING> SmartHomeBridge Python package source not found at $PACKAGE_DIR"
    exit 1
fi

if [ ! -f "$BUILD_REQUIREMENTS_FILE" ] || [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "<WARNING> SmartHomeBridge pinned requirements are incomplete at $PACKAGE_DIR"
    exit 1
fi

cleanup_previous_runtime
VENV_CANDIDATE="$(mktemp -d "${DATA_DIR}/.venv-runtime-XXXXXX")"
VENV_LINK="${VENV_CANDIDATE}.link"
python3 -m venv "$VENV_CANDIDATE"
"$VENV_CANDIDATE/bin/python" -m pip install \
    --requirement "$BUILD_REQUIREMENTS_FILE"
"$VENV_CANDIDATE/bin/python" -m pip install \
    --no-build-isolation \
    --requirement "$REQUIREMENTS_FILE"
"$VENV_CANDIDATE/bin/python" -m pip install \
    --no-build-isolation \
    --no-deps \
    "$PACKAGE_DIR"
"$VENV_CANDIDATE/bin/python" -m pip check
"$VENV_CANDIDATE/bin/python" -c \
    'import smart_home_bridge; import smartcoop; import paho.mqtt.client'

ln -s "$VENV_CANDIDATE" "$VENV_LINK"
previous_runtime=""
if [ -L "$VENV_DIR" ]; then
    previous_runtime="$(readlink -f "$VENV_DIR" 2>/dev/null || true)"
    mv -Tf "$VENV_LINK" "$VENV_DIR"
elif [ -e "$VENV_DIR" ]; then
    previous_runtime="$(mktemp -d "${DATA_DIR}/.venv-legacy-XXXXXX")"
    rmdir "$previous_runtime"
    mv "$VENV_DIR" "$previous_runtime"
    if ! mv "$VENV_LINK" "$VENV_DIR"; then
        mv "$previous_runtime" "$VENV_DIR"
        exit 1
    fi
else
    mv "$VENV_LINK" "$VENV_DIR"
fi
ACTIVATED=true

if [ -n "$previous_runtime" ] && [ -e "$previous_runtime" ]; then
    ln -s "$previous_runtime" "$VENV_PREVIOUS_LINK"
fi

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
echo "<OK> SmartHomeBridge shared runtime installed and validated"
