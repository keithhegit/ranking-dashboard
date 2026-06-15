# Competitor Monitor Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers%20%2B%20D1%20%2B%20R2-f38020)](https://workers.cloudflare.com/)
[![Status](https://img.shields.io/badge/status-active-success)](#operations)
[![Runner](https://img.shields.io/badge/runner-Ubuntu%20Chrome%20Profile-informational)](#ubuntu-runner)

[English](#english) | [中文](#中文)

## English

Competitor Monitor Dashboard is a daily Sensor Tower ranking monitor for cloud
phone competitors. It keeps the browser-login collection layer on an Ubuntu
host, while Cloudflare provides the publishing, data, and dashboard layers.

The dashboard tracks UGPhone, LDCloud, Redfinger, and VSPhone across 20 markets,
then publishes the familiar `dashboard.html` experience through Cloudflare with
fresh data from D1/R2.

### Quick Links

- Production dashboard: <https://ug-ranking-dashboard.keithhe.com>
- Worker fallback: <https://competitor-monitor-dashboard.keithhe2021.workers.dev>
- Cloudflare setup: [docs/cloudflare-setup.md](./docs/cloudflare-setup.md)
- Ubuntu runner guide: [docs/ubuntu-runner.md](./docs/ubuntu-runner.md)
- Runner install script: [linux/install_ubuntu.sh](./linux/install_ubuntu.sh)

### Architecture

```text
Sensor Tower logged-in browser
  -> Ubuntu runner at 00:00 Asia/Shanghai
  -> CSV, logs, screenshots, local dashboard.html
  -> Cloudflare Worker ingest API
  -> D1 ranking tables + R2 raw snapshots
  -> Worker Assets dashboard
```

Cloudflare is intentionally used as the publication, data, and dashboard layer.
The collection runner remains outside Cloudflare because Sensor Tower collection
depends on a real logged-in browser profile.

### Daily Workflow

1. `competitor-monitor.timer` triggers every day at 00:00 Beijing time.
2. The Ubuntu runner opens the persisted Chrome profile.
3. Playwright drives Sensor Tower and collects 4 products x 20 countries.
4. The runner keeps only "Revenue Ranking - Tools".
5. Local artifacts are written under `output/`, `logs/`, and `screenshots/`.
6. The original-style `dashboard.html` is rebuilt locally.
7. Structured results are uploaded to Cloudflare Worker.
8. Worker writes D1 rows and archives the raw payload in R2.
9. The online dashboard reads `/api/dashboard` and renders the latest matrix.

### Cloudflare Resources

The deployed Worker is configured in [wrangler.toml](./wrangler.toml):

- Worker: `competitor-monitor-dashboard`
- Custom domain: `ug-ranking-dashboard.keithhe.com`
- D1 binding: `DB`
- D1 database id: `be38c2d0-f596-46ba-8aee-22c324826f63`
- R2 binding: `SNAPSHOTS`
- R2 bucket: `competitor-monitor-dashboard-snapshots`
- Cron: `0 16 * * *` for 00:00 Beijing time

Deploy:

```bash
npm install
npm test
npm run d1:migrations:apply
npm run deploy
```

### Ubuntu Runner

Remote working directory:

```bash
/home/ubuntu/ranking-dashboard
```

Key services:

```bash
systemctl status competitor-monitor.timer
systemctl status competitor-monitor.service
systemctl status competitor-monitor-browser.service
```

Common operations:

```bash
# Follow today's runner log
journalctl -u competitor-monitor.service --since today -f

# Trigger a manual run
sudo systemctl start competitor-monitor.service

# Check the next scheduled run
systemctl list-timers competitor-monitor.timer
```

noVNC observation tunnel:

```powershell
ssh -L 6080:127.0.0.1:6080 ubuntu@14.136.93.109
```

Then open:

```text
http://127.0.0.1:6080/vnc.html
```

### Local Artifacts

The runner keeps the same operational artifacts as the original local workflow:

- `output/`: daily CSV files, batch CSV files, and batch logs
- `logs/`: scraper diagnostics
- `screenshots/`: page load and hover evidence
- `dashboard.html`: latest local dashboard
- `runtime/browser_profile/`: Sensor Tower login state; never share it

### Operations

To confirm that a daily 00:00 run has finished:

```bash
systemctl is-active competitor-monitor.service
```

The service usually returns `inactive` after completion. A complete daily matrix
targets 80 rows:

```bash
python3 - <<'PY'
import csv
path = '/home/ubuntu/ranking-dashboard/output/sensor_tower_multi_product_multi_country_YYYYMMDD.csv'
with open(path, newline='', encoding='utf-8-sig') as f:
    print(sum(1 for _ in csv.DictReader(f)))
PY
```

Check Cloudflare upload logs:

```bash
journalctl -u competitor-monitor.service --since today | grep -i cloudflare
```

### Security

Do not commit or share:

- `runtime/` browser profiles, cookies, or login state
- real `output/` CSV files
- `logs/` and `screenshots/` from private runs
- `.dev.vars`, `.npmrc`, Worker secrets, API tokens, or account credentials

If a server password was ever pasted into chat, scripts, or terminal logs, rotate
it and move the host to SSH key login.

## 中文

Competitor Monitor Dashboard 是一个面向云手机竞品的 Sensor Tower 每日排名看板。
它把“需要登录浏览器”的采集层放在 Ubuntu 主机上，把发布层、数据层和看板层放在
Cloudflare 上。

当前监测 UGPhone、LDCloud、Redfinger、VSPhone 在 20 个市场的
“收入排行 - 工具”排名。线上页面保留团队习惯使用的原版 `dashboard.html`
视觉样式，只把数据源切换为 D1/R2 每日自动更新结果。

### 快速入口

- 线上看板：<https://ug-ranking-dashboard.keithhe.com>
- Worker 备用地址：<https://competitor-monitor-dashboard.keithhe2021.workers.dev>
- Cloudflare 配置：[docs/cloudflare-setup.md](./docs/cloudflare-setup.md)
- Ubuntu runner 指南：[docs/ubuntu-runner.md](./docs/ubuntu-runner.md)
- Ubuntu 装机脚本：[linux/install_ubuntu.sh](./linux/install_ubuntu.sh)

### 系统架构

```text
Sensor Tower 已登录浏览器
  -> Ubuntu runner 每天北京时间 00:00 执行
  -> CSV、日志、截图、本地 dashboard.html
  -> Cloudflare Worker ingest API
  -> D1 排名表 + R2 原始快照
  -> Worker Assets 在线看板
```

Cloudflare 在本项目中负责发布层、数据层、看板层。采集层保留在 Ubuntu 主机，
因为 Sensor Tower 采集依赖真实浏览器 Profile 和人工登录态。

### 每日流程

1. `competitor-monitor.timer` 每天北京时间 00:00 触发。
2. Ubuntu runner 启动已登录的 Chrome Profile。
3. Playwright 模拟浏览器操作 Sensor Tower。
4. 抓取 4 个产品、20 个国家。
5. 只保留“收入排行 - 工具”。
6. 本地保存 CSV、日志、截图，并重建原版 `dashboard.html`。
7. 采集完成后上传结构化结果到 Cloudflare Worker。
8. Worker 写入 D1，并把原始 payload 归档到 R2。
9. 在线看板通过 `/api/dashboard` 读取最新数据并渲染。

### Cloudflare 资源

[wrangler.toml](./wrangler.toml) 中配置了：

- Worker：`competitor-monitor-dashboard`
- 自定义域名：`ug-ranking-dashboard.keithhe.com`
- D1 binding：`DB`
- D1 database id：`be38c2d0-f596-46ba-8aee-22c324826f63`
- R2 binding：`SNAPSHOTS`
- R2 bucket：`competitor-monitor-dashboard-snapshots`
- Cron：`0 16 * * *`，对应北京时间每日 00:00

部署命令：

```bash
npm install
npm test
npm run d1:migrations:apply
npm run deploy
```

### Ubuntu Runner

远端工作目录：

```bash
/home/ubuntu/ranking-dashboard
```

关键服务：

```bash
systemctl status competitor-monitor.timer
systemctl status competitor-monitor.service
systemctl status competitor-monitor-browser.service
```

常用操作：

```bash
# 查看当天自动任务日志
journalctl -u competitor-monitor.service --since today -f

# 手动触发一次每日采集
sudo systemctl start competitor-monitor.service

# 查看下一次 00:00 自动触发时间
systemctl list-timers competitor-monitor.timer
```

noVNC 观察通道：

```powershell
ssh -L 6080:127.0.0.1:6080 ubuntu@14.136.93.109
```

然后打开：

```text
http://127.0.0.1:6080/vnc.html
```

### 本地产物

Ubuntu runner 会保留原本 Windows 本地流程中的核心产物：

- `output/`：每日 CSV、批次 CSV、批次日志
- `logs/`：采集诊断日志
- `screenshots/`：页面加载和 hover 证据截图
- `dashboard.html`：最新本地看板
- `runtime/browser_profile/`：Sensor Tower 登录态，严禁分享

### 运维检查

确认 00:00 任务是否完成：

```bash
systemctl is-active competitor-monitor.service
```

完成后通常返回 `inactive`。完整全量目标是 80 行：

```bash
python3 - <<'PY'
import csv
path = '/home/ubuntu/ranking-dashboard/output/sensor_tower_multi_product_multi_country_YYYYMMDD.csv'
with open(path, newline='', encoding='utf-8-sig') as f:
    print(sum(1 for _ in csv.DictReader(f)))
PY
```

检查 Cloudflare 上传结果：

```bash
journalctl -u competitor-monitor.service --since today | grep -i cloudflare
```

### Windows 兼容入口

旧入口仍保留，适合本地调试或备用采集：

- `FIRST_RUN_LOGIN.bat`
- `RUN_DAILY.bat`
- `run_daily.ps1`

正式自动化以 Ubuntu runner + Cloudflare 在线看板为准。

### 隐私与安全

以下内容不应提交到 GitHub：

- `runtime/` 浏览器 Profile、Cookie、登录态
- `output/` 真实采集 CSV
- `logs/` 和 `screenshots/` 私有运行产物
- `.dev.vars`、`.npmrc`、Worker secret、API token、账号密码

如果曾经在聊天、脚本或终端中暴露过服务器密码，建议尽快轮换密码并改为
SSH key 登录。
