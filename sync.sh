#!/usr/bin/env bash
# Copy the firmware to a mounted CIRCUITPY drive.
#
#   ./sync.sh            deploy once
#   ./sync.sh --watch    redeploy on every change (needs fswatch)
#
# The drive is auto-detected on macOS and Linux; override with CIRCUITPY=/path.
set -euo pipefail
cd "$(dirname "$0")"

find_drive() {
    for candidate in "${CIRCUITPY:-}" /Volumes/CIRCUITPY "/run/media/${USER}/CIRCUITPY" "/media/${USER}/CIRCUITPY"; do
        if [[ -n "$candidate" && -d "$candidate" ]]; then
            echo "$candidate"
            return
        fi
    done
    echo "CIRCUITPY drive not found; mount the board or set CIRCUITPY=/path" >&2
    exit 1
}

deploy() {
    local drive
    drive="$(find_drive)"
    mkdir -p "$drive/lib" "$drive/mmecu"
    cp -R lib/. "$drive/lib/"
    rm -f "$drive"/mmecu/*.py
    cp mmecu/*.py "$drive/mmecu/"
    # code.py last: writing it triggers CircuitPython's auto-reload
    cp code.py "$drive/code.py"
    sync
    echo "deployed to $drive"
}

if [[ "${1:-}" == "--watch" ]]; then
    deploy
    fswatch -o code.py mmecu lib | while read -r _; do deploy; done
else
    deploy
fi
