#!/usr/bin/env bash
set -Eeuo pipefail

APP_USER="${APP_USER:-$USER}"
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TIMER_CALENDAR="${TIMER_CALENDAR:-*-*-* 00:00:00 Asia/Shanghai}"

if [[ "$(id -u)" -eq 0 && "$APP_USER" == "root" ]]; then
  echo "Do not run the runner as root. Set APP_USER to a normal user." >&2
  exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required." >&2
  exit 1
fi

echo "[1/7] Installing Ubuntu packages"
sudo apt-get update
sudo apt-get install -y \
  ca-certificates curl gnupg software-properties-common \
  xvfb x11vnc fluxbox novnc websockify \
  jq unzip git procps lsof x11-utils

if ! command -v python3.13 >/dev/null 2>&1; then
  echo "[2/7] Installing Python 3.13 from deadsnakes PPA"
  sudo add-apt-repository -y ppa:deadsnakes/ppa
  sudo apt-get update
  sudo apt-get install -y python3.13 python3.13-venv
else
  echo "[2/7] Python 3.13 already installed"
fi

if ! command -v google-chrome >/dev/null 2>&1; then
  echo "[3/7] Installing Google Chrome"
  curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-linux-signing-keyring.gpg
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list >/dev/null
  sudo apt-get update
  sudo apt-get install -y google-chrome-stable
else
  echo "[3/7] Google Chrome already installed"
fi

echo "[4/7] Creating Python virtual environment"
cd "$APP_DIR"
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
python - <<'PY'
import sys
assert sys.version_info[:2] == (3, 13), sys.version
print("Python runtime OK:", sys.version.split()[0])
PY

echo "[5/7] Creating runtime directories"
mkdir -p "$APP_DIR/runtime/browser_profile" "$APP_DIR/logs" "$APP_DIR/output" "$APP_DIR/screenshots"

echo "[6/7] Writing systemd service and timer"
sudo tee /etc/systemd/system/competitor-monitor.service >/dev/null <<EOF
[Unit]
Description=Competitor monitor daily runner
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=-/etc/competitor-monitor.env
ExecStart=$APP_DIR/linux/run_daily.sh
TimeoutStartSec=7200
EOF

sudo tee /etc/systemd/system/competitor-monitor.timer >/dev/null <<EOF
[Unit]
Description=Run competitor monitor daily at 00:00

[Timer]
OnCalendar=$TIMER_CALENDAR
Persistent=true
Unit=competitor-monitor.service

[Install]
WantedBy=timers.target
EOF

if [[ ! -f /etc/competitor-monitor.env ]]; then
  sudo tee /etc/competitor-monitor.env >/dev/null <<'EOF'
# Optional Cloudflare upload after local scrape.
# CLOUDFLARE_WORKER_URL=https://competitor-monitor-dashboard.<your-subdomain>.workers.dev
# CLOUDFLARE_INGEST_TOKEN=replace-with-the-worker-INGEST_TOKEN

DISPLAY=:99
VNC_PORT=5900
NOVNC_PORT=6080
VNC_LISTEN=127.0.0.1
NOVNC_LISTEN=127.0.0.1
EOF
  sudo chmod 600 /etc/competitor-monitor.env
fi

sudo systemctl daemon-reload
sudo systemctl enable competitor-monitor.timer

echo "[7/7] Done"
cat <<EOF

Next steps:
1. Start the login browser:
   $APP_DIR/linux/first_run_login.sh

2. Open noVNC in your browser:
   http://<ubuntu-host>:6080/vnc.html

3. Log in to Sensor Tower in Chrome, then keep the browser profile under:
   $APP_DIR/runtime/browser_profile

4. Test one run:
   systemctl start competitor-monitor.service
   journalctl -u competitor-monitor.service -f

5. The timer is enabled:
   systemctl list-timers competitor-monitor.timer

EOF
