#!/bin/sh
set -eu

COMMAND="${1:-status}"
PLUGIN_FOLDER="${PLUGIN_FOLDER:-{{PLUGIN_FOLDER}}}"
PLUGIN_TITLE="{{PLUGIN_TITLE}}"
ENABLED_DEVICES="{{DEVICE_KEYS}}"
export PLUGIN_FOLDER
export SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry

LBPBIN="${LBPBIN:-./bin}"
LBPCONFIG="${LBPCONFIG:-./config}"
LBHOMEDIR="${LBHOMEDIR:-./loxberry}"
LBPDATA="${LBPDATA:-./data}"
LBPLOG="${LBPLOG:-./logs}"
BIN_DIR="${LBPBIN}/${PLUGIN_FOLDER}"
VENV_BIN="${LBPDATA}/${PLUGIN_FOLDER}/venv/bin"
LOG_DIR="${LBPLOG}/${PLUGIN_FOLDER}"
PID_FILE="${LOG_DIR}/smart-home-bridge.pid"
LOG_FILE="${LOG_DIR}/smart-home-bridge.log"
STARTUP_GRACE_SECONDS="${STARTUP_GRACE_SECONDS:-2}"
export LBPBIN LBPCONFIG LBHOMEDIR LBPDATA LBPLOG
PATH="${VENV_BIN}:${BIN_DIR}:${LBPBIN}:$PATH"

read_bridge_pid() {
    if [ ! -f "$PID_FILE" ]; then
        return 1
    fi
    BRIDGE_PID="$(cat "$PID_FILE")"
    case "$BRIDGE_PID" in
        ''|*[!0-9]*) return 1 ;;
    esac
}

is_bridge_process() {
    bridge_pid="$1"
    if ! kill -0 "$bridge_pid" 2>/dev/null; then
        return 1
    fi
    if [ ! -r "/proc/${bridge_pid}/cmdline" ]; then
        return 1
    fi
    command_line="$(tr '\000' ' ' < "/proc/${bridge_pid}/cmdline")"
    case "$command_line" in
        *smart-home-bridge*) return 0 ;;
        *) return 1 ;;
    esac
}

bridge_is_running() {
    read_bridge_pid && is_bridge_process "$BRIDGE_PID"
}

start_bridge() {
    mkdir -p "$LOG_DIR"
    if bridge_is_running; then
        echo "$PLUGIN_TITLE already running"
        return 0
    fi

    rm -f "$PID_FILE"
    "$VENV_BIN/smart-home-bridge-config-check" >/dev/null
    nohup "$VENV_BIN/smart-home-bridge" >> "$LOG_FILE" 2>&1 &
    BRIDGE_PID="$!"
    printf '%s\n' "$BRIDGE_PID" > "${PID_FILE}.tmp"
    mv "${PID_FILE}.tmp" "$PID_FILE"
    sleep "$STARTUP_GRACE_SECONDS"
    if ! is_bridge_process "$BRIDGE_PID"; then
        exit_code=1
        if kill -0 "$BRIDGE_PID" 2>/dev/null; then
            kill "$BRIDGE_PID"
        fi
        if wait "$BRIDGE_PID" 2>/dev/null; then
            exit_code=0
        else
            exit_code=$?
        fi
        rm -f "$PID_FILE"
        echo "$PLUGIN_TITLE failed to start (exit code $exit_code)" >&2
        return 1
    fi
    echo "$PLUGIN_TITLE started"
}

stop_bridge() {
    if ! read_bridge_pid; then
        echo "$PLUGIN_TITLE is not running"
        return 0
    fi
    if is_bridge_process "$BRIDGE_PID"; then
        kill "$BRIDGE_PID"
    fi
    rm -f "$PID_FILE"
    echo "$PLUGIN_TITLE stopped"
}

service_status() {
    if ! bridge_is_running; then
        rm -f "$PID_FILE"
        echo "$PLUGIN_TITLE is not running" >&2
        return 1
    fi
    "$VENV_BIN/smart-home-bridge-status"
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
        "$VENV_BIN/smart-home-bridge-config-check"
        "$VENV_BIN/smart-home-bridge-status"
        ;;
    is-running)
        bridge_is_running
        ;;
    door-command)
        case ",$ENABLED_DEVICES," in
            *,chicken_door,*) ;;
            *)
                echo "Door commands are not supported by $PLUGIN_TITLE" >&2
                exit 2
                ;;
        esac
        DOOR_COMMAND="${2:-}"
        case "$DOOR_COMMAND" in
            open_door|close_door|stop_door|get_door_state)
                "$VENV_BIN/smart-home-bridge-door-command" "$DOOR_COMMAND"
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
