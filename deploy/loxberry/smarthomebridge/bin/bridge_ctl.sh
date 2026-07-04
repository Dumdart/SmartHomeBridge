#!/bin/sh
set -eu

COMMAND="${1:-status}"
export SMART_HOME_BRIDGE_CONFIG_SOURCE=loxberry

LBPBIN="${LBPBIN:-./bin}"
LBPCONFIG="${LBPCONFIG:-./config}"
LBHOMEDIR="${LBHOMEDIR:-./loxberry}"
LOG_DIR="${LBPLOG:-./logs}"
PID_FILE="${LOG_DIR}/smart-home-bridge.pid"
LOG_FILE="${LOG_DIR}/smart-home-bridge.log"
export LBPBIN LBPCONFIG LBHOMEDIR
PATH="${LBPBIN}:$PATH"

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
        smart-home-bridge-status
        ;;
    dump-config)
        smart-home-bridge-config-check
        smart-home-bridge-status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|dump-config}" >&2
        exit 2
        ;;
esac
