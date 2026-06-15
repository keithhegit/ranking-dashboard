#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DISPLAY="${DISPLAY:-:99}"
export VNC_PORT="${VNC_PORT:-5900}"
export NOVNC_PORT="${NOVNC_PORT:-6080}"
export BROWSER_PROFILE="$ROOT/runtime/browser_profile"

"$ROOT/linux/start_browser_vnc.sh" "https://app.sensortower.com/"

cat <<EOF
Login browser started.

Open:
  http://<ubuntu-host>:$NOVNC_PORT/vnc.html

Then log in to Sensor Tower. The session is stored in:
  $BROWSER_PROFILE
EOF
