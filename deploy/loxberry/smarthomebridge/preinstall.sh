#!/bin/sh
set -eu

if command -v python3 >/dev/null 2>&1; then
    echo "<OK> python3 found"
else
    echo "<WARNING> python3 not found. Install python3 before starting SmartHomeBridge."
    exit 1
fi

echo "<INFO> SmartHomeBridge preinstall checks completed"
