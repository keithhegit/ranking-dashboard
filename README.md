# Cloud Phone Competitor Ranking Dashboard

Sensor Tower 云手机竞品排名自动采集与 Cloudflare 在线看板。当前监测 UGPhone、LDCloud、Redfinger、VSPhone 在 20 个市场的“收入排行 - 工具”排名。

## 当前线上流程

旧版仓库的流程是 Windows 本地双击 `RUN_DAILY.bat`，采集后生成本机 `dashboard.html` 并打开 `http://127.0.0.1:8765/dashboard.html`。

现在流程已经改为：

1. Ubuntu runner 每天北京时间 00:00 由 `competitor-monitor.timer` 自动触发。
2. Runner 启动已登录的 Chrome Profile，并通过 Playwright 模拟鼠标操作 Sensor Tower。
3. 抓取 4 个产品、20 个国家，只保留“收入排行 - 工具”。
4. Ubuntu 本地仍然保存 CSV、日志、截图，并重建原版 `dashboard.html`。
5. 采集完成后，Runner 将结构化结果上传到 Cloudflare Worker。
6. Worker 写入 D1，并把原始 payload 归档到 R2。
7. 团队直接访问 Cloudflare 托管的在线看板查看最新数据。

## 在线看板

当前 Worker 地址：

- `https://competitor-monitor-dashboard.keithhe2021.workers.dev`

自定义域名：

- `https://ug-ranking-dashboard.keithhe.com`

线上页面使用原 `dashboard.html` 的视觉样式和交互习惯，数据源改为 `/api/dashboard`，由 D1 中最新采集结果自动驱动。

## Ubuntu Runner

远端目录：

- `/home/ubuntu/ranking-dashboard`

关键服务：

```bash
systemctl status competitor-monitor.timer
systemctl status competitor-monitor.service
systemctl status competitor-monitor-browser.service
```

常用命令：

```bash
# 查看当天自动任务日志
journalctl -u competitor-monitor.service --since today -f

# 手动触发一次每日采集
sudo systemctl start competitor-monitor.service

# 查看下一次 00:00 自动触发时间
systemctl list-timers competitor-monitor.timer
```

浏览器观察通道：

```powershell
ssh -L 6080:127.0.0.1:6080 ubuntu@14.136.93.109
```

然后在 Windows 浏览器打开：

```text
http://127.0.0.1:6080/vnc.html
```

## 输出目录

Ubuntu runner 会保留原仓库的本地产物：

- `output/`：每日 CSV、批次 CSV、批次日志
- `logs/`：抓取诊断日志
- `screenshots/`：页面加载和 hover 证据截图
- `dashboard.html`：原版本地看板
- `runtime/browser_profile/`：Sensor Tower 登录态，严禁分享

Cloudflare 侧保存：

- D1：结构化排名数据和每日 run 状态
- R2：每日上传的原始 JSON snapshot
- Worker Assets：在线看板前端

## Cloudflare 资源

Wrangler 配置在 `wrangler.toml`：

- Worker：`competitor-monitor-dashboard`
- D1 binding：`DB`
- D1 database id：`be38c2d0-f596-46ba-8aee-22c324826f63`
- R2 binding：`SNAPSHOTS`
- R2 bucket：`competitor-monitor-dashboard-snapshots`
- Custom domain：`ug-ranking-dashboard.keithhe.com`
- Cron：`0 16 * * *`，对应北京时间每日 00:00

部署命令：

```bash
npm install
npm test
npm run d1:migrations:apply
npm run deploy
```

`INGEST_TOKEN` 是 Worker secret，Ubuntu runner 通过 `/etc/competitor-monitor.env` 持有同一 token。不要把 token 写入仓库。

## 如何确认 00:00 任务已完成

1. 看 systemd 服务是否结束：

```bash
systemctl is-active competitor-monitor.service
```

完成后通常会返回 `inactive`。

2. 看当天 CSV 行数：

```bash
python3 - <<'PY'
import csv
path = '/home/ubuntu/ranking-dashboard/output/sensor_tower_multi_product_multi_country_YYYYMMDD.csv'
with open(path, newline='', encoding='utf-8-sig') as f:
    print(sum(1 for _ in csv.DictReader(f)))
PY
```

完整全量目标是 80 行。

3. 看上传结果：

```bash
journalctl -u competitor-monitor.service --since today | grep -i cloudflare
```

正常情况下会看到 Cloudflare upload start/finished，Worker 返回 `accepted`。

4. 打开在线看板：

```text
https://ug-ranking-dashboard.keithhe.com
```

如果自定义域名刚配置，短时间内也可以先看：

```text
https://competitor-monitor-dashboard.keithhe2021.workers.dev
```

## Windows 本地兼容入口

旧入口仍保留：

- `FIRST_RUN_LOGIN.bat`
- `RUN_DAILY.bat`
- `run_daily.ps1`

它们适合本地调试或备用采集。正式自动化以 Ubuntu runner + Cloudflare 看板为准。

## 隐私与发布

以下内容不应提交到 GitHub：

- `runtime/` 浏览器 Profile、Cookie、登录态
- `output/` 真实采集 CSV
- `logs/` 日志
- `screenshots/` 证据截图
- `.dev.vars`、`.npmrc`、任何 token 或账号信息

如果曾经在聊天、脚本或终端中暴露过服务器密码，建议尽快轮换密码并改为 SSH key 登录。
