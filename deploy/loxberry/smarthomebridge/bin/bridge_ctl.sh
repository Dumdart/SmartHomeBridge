#!/bin/sh
set -eu

COMMAND="${1:-status}"
export SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry

PLUGIN_FOLDER="${PLUGIN_FOLDER:-smarthomebridge}"
LBPBIN="${LBPBIN:-./bin}"
LBPCONFIG="${LBPCONFIG:-./config}"
LBHOMEDIR="${LBHOMEDIR:-./loxberry}"
LBPDATA="${LBPDATA:-./data}"
BIN_DIR="${LBPBIN}/${PLUGIN_FOLDER}"
VENV_BIN="${LBPDATA}/${PLUGIN_FOLDER}/venv/bin"
INFERENCE_VENV_BIN="${LBPDATA}/${PLUGIN_FOLDER}/inference-venv/bin"
LOG_DIR="${LBPLOG:-./logs}/${PLUGIN_FOLDER}"
PID_FILE="${LOG_DIR}/smart-home-bridge.pid"
INFERENCE_PID_FILE="${LOG_DIR}/smart-home-inference.pid"
LOG_FILE="${LOG_DIR}/smart-home-bridge.log"
INFERENCE_LOG_FILE="${LOG_DIR}/smart-home-inference.log"
export LBPBIN LBPCONFIG LBHOMEDIR LBPDATA
PATH="${VENV_BIN}:${INFERENCE_VENV_BIN}:${BIN_DIR}:${LBPBIN}:$PATH"

start_bridge() {
    mkdir -p "$LOG_DIR"
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "SmartHomeBridge already running"
        return 0
    fi
    nohup smart-home-bridge >> "$LOG_FILE" 2>&1 &
    echo "$!" > "$PID_FILE"
    echo "SmartHomeBridge started"
}

start_inference() {
    mkdir -p "$LOG_DIR"
    if [ -f "$INFERENCE_PID_FILE" ] && kill -0 "$(cat "$INFERENCE_PID_FILE")" 2>/dev/null; then
        echo "SmartHomeBridge inference already running"
        return 0
    fi
    nohup smart-home-inference >> "$INFERENCE_LOG_FILE" 2>&1 &
    echo "$!" > "$INFERENCE_PID_FILE"
    echo "SmartHomeBridge inference started"
}

stop_bridge() {
    if [ ! -f "$PID_FILE" ]; then
        echo "SmartHomeBridge is not running"
        return 0
    fi
    PID="$(cat "$PID_FILE")"
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
    fi
    rm -f "$PID_FILE"
    echo "SmartHomeBridge stopped"
}

stop_inference() {
    if [ ! -f "$INFERENCE_PID_FILE" ]; then
        echo "SmartHomeBridge inference is not running"
        return 0
    fi
    PID="$(cat "$INFERENCE_PID_FILE")"
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
    fi
    rm -f "$INFERENCE_PID_FILE"
    echo "SmartHomeBridge inference stopped"
}

service_status() {
    smart-home-bridge-status
    if [ -f "$INFERENCE_PID_FILE" ] && kill -0 "$(cat "$INFERENCE_PID_FILE")" 2>/dev/null; then
        echo "SmartHomeBridge inference running"
    else
        echo "SmartHomeBridge inference is not running"
    fi
}

case "$COMMAND" in
    start)
        start_inference
        start_bridge
        ;;
    stop)
        stop_bridge
        stop_inference
        ;;
    restart)
        stop_bridge
        stop_inference
        start_inference
        start_bridge
        ;;
    start-bridge)
        start_bridge
        ;;
    stop-bridge)
        stop_bridge
        ;;
    start-inference)
        start_inference
        ;;
    stop-inference)
        stop_inference
        ;;
    status)
        service_status
        ;;
    dump-config)
        smart-home-bridge-config-check
        smart-home-bridge-status
        ;;
    door-command)
        DOOR_COMMAND="${2:-}"
        case "$DOOR_COMMAND" in
            open_door|close_door|stop_door|get_door_state)
                smart-home-bridge-door-command "$DOOR_COMMAND"
                ;;
            *)
                echo "Usage: $0 door-command {open_door|close_door|stop_door|get_door_state}" >&2
                exit 2
                ;;
        esac
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|start-bridge|stop-bridge|start-inference|stop-inference|status|dump-config|door-command}" >&2
        exit 2
        ;;
esac
