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
LOG_DIR="${LBPLOG:-./logs}/${PLUGIN_FOLDER}"
PID_FILE="${LOG_DIR}/smart-home-bridge.pid"
LOG_FILE="${LOG_DIR}/smart-home-bridge.log"
export LBPBIN LBPCONFIG LBHOMEDIR LBPDATA
PATH="${VENV_BIN}:${BIN_DIR}:${LBPBIN}:$PATH"

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

service_status() {
    smart-home-bridge-status
}

case "$COMMAND" in
    start)
        start_bridge
        ;;
    stop)
        stop_bridge
        ;;
    restart)
        stop_bridge
        start_bridge
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
        echo "Usage: $0 {start|stop|restart|status|dump-config|door-command}" >&2
        exit 2
        ;;
esac
