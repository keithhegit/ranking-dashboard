#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DISPLAY="${DISPLAY:-:99}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
VNC_LISTEN="${VNC_LISTEN:-127.0.0.1}"
NOVNC_LISTEN="${NOVNC_LISTEN:-127.0.0.1}"
BROWSER_PROFILE="${BROWSER_PROFILE:-$ROOT/runtime/browser_profile}"
START_URL="${START_URL:-https://app.sensortower.com/}"
LOG_DIR="$ROOT/logs/linux"

mkdir -p "$BROWSER_PROFILE" "$LOG_DIR"

children=()
cleanup() {
  for pid in "${children[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT INT TERM

Xvfb "$DISPLAY" -screen 0 1920x1080x24 -nolisten tcp >"$LOG_DIR/xvfb.service.log" 2>&1 &
children+=("$!")
sleep 1

env DISPLAY="$DISPLAY" fluxbox >"$LOG_DIR/fluxbox.service.log" 2>&1 &
children+=("$!")

if [[ -n "${VNC_PASSWORD:-}" ]]; then
  PASSFILE="$ROOT/runtime/x11vnc.pass"
  x11vnc -storepasswd "$VNC_PASSWORD" "$PASSFILE" >/dev/null
  x11vnc -display "$DISPLAY" -listen "$VNC_LISTEN" -rfbport "$VNC_PORT" -rfbauth "$PASSFILE" -forever -shared >"$LOG_DIR/x11vnc.service.log" 2>&1 &
else
  x11vnc -display "$DISPLAY" -listen "$VNC_LISTEN" -rfbport "$VNC_PORT" -forever -shared -nopw >"$LOG_DIR/x11vnc.service.log" 2>&1 &
fi
children+=("$!")

if command -v novnc_proxy >/dev/null 2>&1; then
  novnc_proxy --listen "$NOVNC_LISTEN:$NOVNC_PORT" --vnc "localhost:$VNC_PORT" >"$LOG_DIR/novnc.service.log" 2>&1 &
elif [[ -x /usr/share/novnc/utils/novnc_proxy ]]; then
  /usr/share/novnc/utils/novnc_proxy --listen "$NOVNC_LISTEN:$NOVNC_PORT" --vnc "localhost:$VNC_PORT" >"$LOG_DIR/novnc.service.log" 2>&1 &
else
  websockify --web=/usr/share/novnc/ "$NOVNC_LISTEN:$NOVNC_PORT" "localhost:$VNC_PORT" >"$LOG_DIR/novnc.service.log" 2>&1 &
fi
children+=("$!")

CHROME="$(command -v google-chrome || command -v google-chrome-stable || command -v chromium || command -v chromium-browser)"
env DISPLAY="$DISPLAY" "$CHROME" \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port=9222 \
  --user-data-dir="$BROWSER_PROFILE" \
  --no-first-run \
  --no-default-browser-check \
  --disable-dev-shm-usage \
  "$START_URL" >"$LOG_DIR/chrome.service.log" 2>&1 &
children+=("$!")

wait -n
