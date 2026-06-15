# Ubuntu Runner

Cloudflare can host the dashboard, API, D1, and R2 archive, but the Sensor Tower collector still needs a real browser profile. This runner lets that browser live on Ubuntu instead of a Windows VPS.

## What This Installs

- Python 3.13 and project dependencies.
- Google Chrome.
- Xvfb, fluxbox, x11vnc, and noVNC for first login.
- A persistent browser profile at `runtime/browser_profile`.
- A `competitor-monitor.timer` systemd timer that runs daily at `00:00 Asia/Shanghai`.

## Install

Copy this repository to the Ubuntu host, then run:

```bash
chmod +x linux/*.sh
APP_USER="$USER" ./linux/install_ubuntu.sh
```

The installer assumes it is run from this repository. If your server should run on another timezone, pass:

```bash
TIMER_TIMEZONE=UTC APP_USER="$USER" ./linux/install_ubuntu.sh
```

## First Login

Start the browser and VNC bridge:

```bash
./linux/first_run_login.sh
```

Open this from your workstation:

```text
http://<ubuntu-host>:6080/vnc.html
```

Log in to Sensor Tower in Chrome. The login state is stored under `runtime/browser_profile`.

Set `VNC_PASSWORD` in `/etc/competitor-monitor.env` if this port is reachable from the public internet. A firewall or SSH tunnel is strongly recommended.

## Cloudflare Upload

Edit `/etc/competitor-monitor.env`:

```bash
CLOUDFLARE_WORKER_URL=https://competitor-monitor-dashboard.<your-subdomain>.workers.dev
CLOUDFLARE_INGEST_TOKEN=<same token as Worker INGEST_TOKEN>
DISPLAY=:99
VNC_PORT=5900
NOVNC_PORT=6080
```

Then test:

```bash
sudo systemctl start competitor-monitor.service
sudo journalctl -u competitor-monitor.service -f
```

Check the timer:

```bash
systemctl list-timers competitor-monitor.timer
```

## Caveat

The compiled scraper engine is only available as `.pyc`. This setup installs the matching Python 3.13 runtime and a Linux browser environment, but if the `.pyc` contains Windows-only assumptions, the scraper itself may still need a replacement collector or source release from the original author.
