#!/usr/bin/env bash
# Copy the firmware to a mounted CIRCUITPY drive (see tools/circuitpy.py).
#
#   ./sync.sh            deploy the working tree and verify
#   ./sync.sh --watch    redeploy on every change (needs fswatch)
#
# The drive is auto-detected on macOS and Linux; override with CIRCUITPY=/path.
# Put known-good firmware back with `make restore` (deploys git master).
set -euo pipefail
cd "$(dirname "$0")"

python3 -m tools.circuitpy deploy
if [[ "${1:-}" == "--watch" ]]; then
    fswatch -o code.py mmecu lib | while read -r _; do
        python3 -m tools.circuitpy deploy
    done
fi
