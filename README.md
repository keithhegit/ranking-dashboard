# Cloud Phone Competitor Ranking Dashboard

Windows 上的 Sensor Tower 云手机竞品排名采集与静态看板工具。当前监测 UGphone、LDCloud、Redfinger、VSPhone 在 20 个市场的“收入排行 - 工具”排名。

本仓库同时包含 Cloudflare 托管改造骨架：Worker 定时任务、D1 数据库、R2 原始快照归档、以及由 Worker Assets 托管的前端页面。Cloudflare Cron 已按北京时间每日 00:00 设计；因为现有采集引擎依赖本机浏览器登录和 CPython 3.13 `.pyc`，实际采集数据需要通过 JSON Feed 或本机上传桥接进入 Worker。详见 `docs/cloudflare-setup.md`。

## 使用条件

- Windows 10/11 64 位
- Microsoft Edge 或 Google Chrome
- Python 3.13 64 位
- 可正常访问排名页面的 Sensor Tower 账号
- 遵守 Sensor Tower 的服务条款和所在组织的数据使用规则

抓取引擎是 CPython 3.13 编译文件，因此其他 Python 版本不能运行。

## 第一次使用

1. 下载 GitHub ZIP 并完整解压。不要直接在压缩包内运行。
2. 双击 `FIRST_RUN_LOGIN.bat`。
3. 脚本会创建 `.venv` 并安装依赖。
4. 浏览器会打开 Sensor Tower。手动登录账号，并确认可以看到应用排名页面。
5. 回到命令窗口按 Enter。

登录信息只保存在当前电脑的 `runtime/browser_profile`，不会上传到 GitHub。

为了让自动化稳定连接，工具使用独立的 Edge/Chrome Profile，而不是复制系统默认浏览器的 Cookie。浏览器仍然是电脑已安装的 Edge 或 Chrome。

## 每日运行

双击 `RUN_DAILY.bat`。脚本会：

1. 启动已登录的浏览器 Profile。
2. 抓取 4 个产品、20 个国家。
3. 仅保存“收入排行 - 工具”。
4. 合并批次结果并生成 CSV。
5. 重建 `dashboard.html`。
6. 启动本地网页并打开 `http://127.0.0.1:8765/dashboard.html`。

运行可能需要一小时以上。不要关闭自动启动的浏览器窗口或命令窗口。

## Cloudflare 自动化托管

Cloudflare 部署入口：

1. 安装依赖：`npm install`
2. 创建 D1/R2 并把 D1 `database_id` 写入 `wrangler.toml`
3. 设置 `INGEST_TOKEN`，可选设置 `SENSOR_TOWER_FEED_URL`
4. 执行 D1 migration：`npm run d1:migrations:apply`
5. 部署：`npm run deploy`

如果暂时没有 Sensor Tower JSON Feed，可以继续使用现有 Windows 采集器，并让 `run_daily.ps1` 在抓取结束后自动上传到 Cloudflare：传入 `-CloudflareWorkerUrl` 和 `-CloudflareIngestToken`，或设置环境变量 `CLOUDFLARE_WORKER_URL` / `CLOUDFLARE_INGEST_TOKEN`。Worker 的 `POST /api/ingest` 会写入 D1，并把原始 JSON 存到 R2。

不想使用 Windows VPS 时，可以用 Ubuntu 作为采集 runner。详见 `docs/ubuntu-runner.md`，它会安装 Chrome、Python 3.13、VNC 首次登录环境和 systemd 每日定时任务。

## 输出目录

- `output/`：每日 CSV 和批次日志
- `logs/`：抓取诊断日志
- `screenshots/`：抓取证据截图
- `dashboard.html`：最新看板
- `runtime/browser_profile/`：本机登录状态，严禁分享

## 常见问题

### Python 3.13 未安装

从 [python.org](https://www.python.org/downloads/) 安装 Python 3.13 64 位，并勾选 Python Launcher。安装后重新运行 `FIRST_RUN_LOGIN.bat`。

### 页面显示未登录

重新运行 `FIRST_RUN_LOGIN.bat`，在自动打开的浏览器窗口中登录。

### 页面出现空白排名

对应任务可能是 `MISSING`、页面加载失败，或者趋势图没有可捕获的 tooltip。查看 `output/daily_all_YYYYMMDD/daily_all.log` 和数据管理页。

### 端口被占用

工具使用本机端口 `9222` 连接浏览器、使用 `8765` 提供 dashboard。关闭占用这些端口的程序后重试。

## 隐私与发布

以下内容已被 `.gitignore` 排除，不应提交：

- 浏览器 Profile、Cookie 和登录状态
- 抓取结果 CSV
- 日志与截图
- Python 虚拟环境
- 生成后的 dashboard

不要将自己的 `runtime/`、`logs/`、`screenshots/` 或真实数据文件上传到公开仓库。

