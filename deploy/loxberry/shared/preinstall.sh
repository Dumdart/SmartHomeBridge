#!/bin/sh
set -eu

if command -v python3 >/dev/null 2>&1; then
    echo "<OK> python3 found"
else
    echo "<WARNING> python3 not found. Install python3 before starting {{PLUGIN_TITLE}}."
    exit 1
fi

if python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
    echo "<OK> python3 version is supported"
else
    echo "<WARNING> python3 3.11 or newer is required for {{PLUGIN_TITLE}}."
    exit 1
fi

if python3 -m venv --help >/dev/null 2>&1; then
    echo "<OK> python3 venv support found"
else
    echo "<WARNING> python3 venv support not found. Install python3-venv before starting {{PLUGIN_TITLE}}."
    exit 1
fi

echo "<INFO> {{PLUGIN_TITLE}} preinstall checks completed"
