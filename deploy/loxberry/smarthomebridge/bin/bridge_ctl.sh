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
    if [ ! -x "$INFERENCE_VENV_BIN/smart-home-inference" ]; then
        echo "SmartHomeBridge inference is not installed. Use Docker inference or install the inference extra on a host with enough disk space."
        return 1
    fi
    if ! "$INFERENCE_VENV_BIN/python" -c 'import ultralytics, uvicorn' >/dev/null 2>&1; then
        echo "SmartHomeBridge inference dependencies are incomplete. Install smart-home-bridge[inference] in the inference venv or use Docker inference."
        return 1
    fi
    if [ -f "$INFERENCE_PID_FILE" ] && kill -0 "$(cat "$INFERENCE_PID_FILE")" 2>/dev/null; then
        echo "SmartHomeBridge inference already running"
        return 0
    fi
    nohup "$INFERENCE_VENV_BIN/smart-home-inference" >> "$INFERENCE_LOG_FILE" 2>&1 &
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
        start_bridge
        ;;
    stop)
        stop_bridge
        stop_inference
        ;;
    restart)
        stop_bridge
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
    install-inference)
        echo "LoxBerry plugin install does not install inference dependencies because Torch/Ultralytics can require multiple GB of disk space."
        echo "Run the inference service with Docker or install smart-home-bridge[inference] manually on a larger host."
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
        echo "Usage: $0 {start|stop|restart|start-bridge|stop-bridge|start-inference|stop-inference|install-inference|status|dump-config|door-command}" >&2
        exit 2
        ;;
esac
