import csv
import glob
import json
import os
import re
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DETAIL_PATTERN = os.path.join(OUTPUT_DIR, "sensor_tower_multi_product_multi_country_*.csv")
SUMMARY_PATTERN = os.path.join(OUTPUT_DIR, "sensor_tower_multi_product_summary_*.csv")
CRAWL_QUEUE_CSV = os.path.join(OUTPUT_DIR, "crawl_queue.csv")
MONITOR_STRATEGY_PATH = os.path.join(BASE_DIR, "config", "monitor_strategy.json")
MARKET_TIERS_PATH = os.path.join(BASE_DIR, "config", "market_tiers.json")
DEFAULT_DAYS = 30
STALE_AFTER_DAYS = 14

BRAND_ORDER = ["ugphone", "ldcloud", "redfinger", "vsphone"]
DEFAULT_MARKET_TIERS = {
    "tiers": {
        "core": {"label": "重点市场", "countries": ["TH", "BR", "PH", "US", "VN", "TR", "MX", "HK", "TW"]},
        "secondary": {"label": "次级市场", "countries": ["ID", "KR", "JP", "DE", "GB", "PL", "FR", "MY", "IT"]},
        "potential": {"label": "潜力市场", "countries": ["SG", "IN"]},
    },
    "country_names": {
        "TH": "泰国",
        "BR": "巴西",
        "PH": "菲律宾",
        "US": "美国",
        "VN": "越南",
        "TR": "土耳其",
        "MX": "墨西哥",
        "HK": "香港",
        "TW": "台湾",
        "ID": "印度尼西亚",
        "KR": "韩国",
        "JP": "日本",
        "DE": "德国",
        "GB": "英国",
        "PL": "波兰",
        "FR": "法国",
        "MY": "马来西亚",
        "IT": "意大利",
        "SG": "新加坡",
        "IN": "印度",
    },
}


def load_market_tiers():
    data = dict(DEFAULT_MARKET_TIERS)
    if os.path.exists(MARKET_TIERS_PATH):
        try:
            with open(MARKET_TIERS_PATH, "r", encoding="utf-8-sig") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data.update(loaded)
        except Exception:
            pass
    return data


MARKET_TIERS = load_market_tiers()
COUNTRY_ORDER = [
    country
    for tier in (MARKET_TIERS.get("tiers") or {}).values()
    for country in (tier.get("countries") or [])
]
APP_IDS = {
    "ugphone": "com.tykeji.ugphone",
    "ldcloud": "com.ld.cph.gl",
    "vsphone": "com.vsphone.overseas",
    "redfinger": "com.redfinger.global",
}
FETCH_MODE_LABELS = {
    "daily_core": "每日核心监测",
    "weekly_potential": "每周潜力监测",
    "biweekly_full": "双周全量监测",
    "Daily Core": "每日核心监测",
    "Weekly Potential": "每周潜力监测",
    "Biweekly Full": "双周全量监测",
}

SUCCESS = "SUCCESS"
PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
FAILED_STATUSES = {"TOOLTIP_PARSE_FAILED", "RANK_CAPTURE_FAILED"}
HISTORY_FALLBACK = "HISTORY_FALLBACK"
STALE_HISTORY = "STALE_HISTORY"
PENDING_TODAY = "PENDING_TODAY"
RATE_LIMITED = "RATE_LIMITED"
QUALITY_VERIFIED = "verified"
QUALITY_NEED_REVIEW = "need_review"
QUALITY_REJECTED = "rejected"
QUALITY_HISTORICAL = "historical"
QUALITY_EXPIRED = "expired"


def market_tier_for(country: str):
    country = (country or "").upper()
    for key, tier in (MARKET_TIERS.get("tiers") or {}).items():
        if country in (tier.get("countries") or []):
            return tier.get("label") or key
    return ""


def country_display_name(country: str):
    country = (country or "").upper()
    name = (MARKET_TIERS.get("country_names") or {}).get(country, "")
    return f"{name} {country}".strip() if name else country


def load_monitor_strategy():
    default = {
        "default_mode": "daily_core",
        "core_countries": ["TH", "PH", "VN", "BR", "ID", "KR", "PL", "JP", "DE", "US"],
        "potential_countries": ["MY", "IN", "IT", "FR", "GB"],
        "full_countries": COUNTRY_ORDER,
    }
    if not os.path.exists(MONITOR_STRATEGY_PATH):
        return default
    try:
        with open(MONITOR_STRATEGY_PATH, "r", encoding="utf-8-sig") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            default.update(loaded)
    except Exception:
        pass
    return default


def fetch_mode_label(value: str):
    value = (value or "").strip()
    return FETCH_MODE_LABELS.get(value, value or "")


def parse_date_from_filename(path: str):
    base = os.path.basename(path)
    match = re.search(r"_(\d{8})(?:_[A-Za-z0-9_-]+)?\.csv$", base)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y%m%d").date()


def to_int(value):
    try:
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            return None
        return int(float(value))
    except Exception:
        return None


def read_csv_rows(path: str):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def get_latest_file(pattern: str):
    dated = []
    for path in glob.glob(pattern):
        day = parse_date_from_filename(path)
        if day:
            dated.append((day, os.path.getmtime(path), path))
    if not dated:
        return None
    dated.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return dated[0][2]


def read_queue_rows():
    if not os.path.exists(CRAWL_QUEUE_CSV) or os.path.getsize(CRAWL_QUEUE_CSV) <= 0:
        return []
    try:
        return read_csv_rows(CRAWL_QUEUE_CSV)
    except Exception:
        return []


def source_url(brand: str, country: str, existing: str = ""):
    if existing:
        return existing
    app_id = APP_IDS.get(brand, "")
    if not app_id or not country:
        return ""
    return f"https://app.sensortower.com/overview/{app_id}?country={country}&tab=category_rankings"


def normalize_status(row: dict):
    has_rank = to_int(row.get("revenue_rank_tools")) is not None
    tooltip_date = (row.get("tooltip_date") or "").strip()
    status = (row.get("status") or "").strip() or "FAILED"
    if status == SUCCESS and (not tooltip_date or not has_rank):
        return "RANK_CAPTURE_FAILED"
    return status


def normalize_quality(row: dict, status: str):
    quality = (row.get("data_quality_status") or "").strip()
    if quality:
        return quality
    if status == SUCCESS and row_has_rank(row):
        return QUALITY_VERIFIED
    if status in (HISTORY_FALLBACK, PENDING_TODAY):
        return QUALITY_HISTORICAL
    if status == STALE_HISTORY:
        return QUALITY_EXPIRED
    if status == PARTIAL_SUCCESS:
        return QUALITY_NEED_REVIEW
    if status in FAILED_STATUSES or status == RATE_LIMITED:
        return QUALITY_NEED_REVIEW
    return QUALITY_NEED_REVIEW if status else ""


def is_official_quality(row: dict):
    return row.get("data_quality_status") in (QUALITY_VERIFIED, QUALITY_HISTORICAL)


def is_review_status(status: str):
    if status in (HISTORY_FALLBACK, PENDING_TODAY):
        return False
    if status == STALE_HISTORY:
        return True
    return status == PARTIAL_SUCCESS or status in FAILED_STATUSES or status not in (
        SUCCESS,
        PARTIAL_SUCCESS,
        "DATA_NOT_VISIBLE",
        HISTORY_FALLBACK,
        STALE_HISTORY,
        PENDING_TODAY,
    )


def load_recent_summary_records(days: int = DEFAULT_DAYS):
    dated_files = []
    for path in glob.glob(SUMMARY_PATTERN):
        day = parse_date_from_filename(path)
        if day:
            dated_files.append((day, os.path.getmtime(path), path))
    dated_files.sort(key=lambda item: (item[0], item[1]), reverse=True)

    latest_per_date = {}
    for day, mtime, path in dated_files:
        if day not in latest_per_date:
            latest_per_date[day] = (day, mtime, path)
    recent = sorted(latest_per_date.values(), key=lambda item: item[0], reverse=True)[:days]

    records = []
    for day, _, path in sorted(recent, key=lambda item: item[0]):
        try:
            rows = read_csv_rows(path)
        except Exception:
            continue
        for row in rows:
            status = normalize_status(row)
            quality = normalize_quality(row, status)
            if quality not in (QUALITY_VERIFIED, QUALITY_HISTORICAL):
                continue
            if not row_has_rank(row):
                continue
            records.append(
                {
                    "date": day.strftime("%Y-%m-%d"),
                    "brand": row.get("brand", ""),
                    "country": row.get("country", ""),
                    "country_display": country_display_name(row.get("country", "")),
                    "market_tier": row.get("market_tier", "") or market_tier_for(row.get("country", "")),
                    "tooltip_date": row.get("tooltip_date", ""),
                    "revenue_rank_tools": to_int(row.get("revenue_rank_tools")),
                    "revenue_rank_apps": None,
                    "top_free_rank_tools": None,
                    "latest_fetch_date": row.get("latest_fetch_date", "") or day.strftime("%Y-%m-%d"),
                    "fetch_mode": fetch_mode_label(row.get("fetch_mode", "")) or "Historical",
                    "status": status,
                    "status_detail": row.get("status_detail", ""),
                    "data_quality_status": quality,
                    "data_quality_detail": row.get("data_quality_detail", ""),
                    "source_url": source_url(row.get("brand", ""), row.get("country", ""), row.get("source_url", "")),
                }
            )
    return records


def row_has_rank(row: dict):
    return to_int(row.get("revenue_rank_tools")) is not None


def parse_rank_date(value: str, reference_date: str = ""):
    value = (value or "").strip()
    if not value:
        return None
    ref = parse_iso_date(reference_date) or datetime.now().date()
    iso = parse_iso_date(value)
    if iso:
        return iso
    match = re.match(r"^([A-Za-z]+)\s+(\d{1,2})(?:,\s*(\d{4}))?$", value)
    if match:
        months = {
            "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
            "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
            "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
            "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
        }
        month = months.get(match.group(1).lower())
        if month:
            year = int(match.group(3)) if match.group(3) else ref.year
            parsed = datetime(year, month, int(match.group(2))).date()
            if not match.group(3) and parsed > ref + timedelta(days=7):
                parsed = parsed.replace(year=ref.year - 1)
            return parsed
    return None


def needs_manual_review(row: dict, current_date: str):
    if not row_has_rank(row):
        return False
    current = parse_iso_date(current_date)
    rank_date = parse_rank_date(row.get("tooltip_date", ""), current_date)
    if not current or not rank_date:
        return True
    return rank_date != current


def latest_history_by_task(series_rows):
    latest = {}
    for row in series_rows:
        if not row.get("brand") or not row.get("country") or not row_has_rank(row) or not is_official_quality(row):
            continue
        key = (row["brand"], row["country"])
        current = latest.get(key)
        if not current or row.get("date", "") >= current.get("date", ""):
            latest[key] = row
    return latest


def parse_iso_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def is_history_stale(history_row: dict):
    fetch_day = parse_iso_date(history_row.get("latest_fetch_date", "") or history_row.get("date", ""))
    if not fetch_day:
        return False
    return fetch_day < datetime.now().date() - timedelta(days=STALE_AFTER_DAYS)


def configured_task_keys():
    return [(brand, country) for brand in BRAND_ORDER for country in COUNTRY_ORDER]


def normalize_latest_detail_row(row, monitor_date: str = ""):
    brand = row.get("brand", "")
    country = row.get("country", "")
    status = normalize_status(row)
    quality = normalize_quality(row, status)
    if status == SUCCESS and quality != QUALITY_VERIFIED:
        status = "RANK_CAPTURE_FAILED"
        quality = QUALITY_NEED_REVIEW
    fetch_date = row.get("latest_fetch_date", "") or (row.get("crawl_time", "")[:10] if row.get("crawl_time") else "") or monitor_date
    return {
        "date": monitor_date or fetch_date,
        "brand": brand,
        "package": row.get("package", "") or APP_IDS.get(brand, ""),
        "country": country,
        "country_display": country_display_name(country),
        "market_tier": row.get("market_tier", "") or market_tier_for(country),
        "tooltip_date": row.get("tooltip_date", ""),
        "app_name": row.get("app_name", ""),
        "revenue_rank_tools": to_int(row.get("revenue_rank_tools")),
        "revenue_rank_apps": None,
        "top_free_rank_tools": None,
        "status": status,
        "status_detail": row.get("status_detail", ""),
        "error_message": row.get("error_message", ""),
        "source_url": source_url(brand, country, row.get("source_url", "")),
        "raw_tooltip_text": row.get("raw_tooltip_text", ""),
        "screenshot_path": row.get("screenshot_path", ""),
        "latest_fetch_date": fetch_date,
        "fetch_mode": fetch_mode_label(row.get("fetch_mode", "")) or "每日核心监测",
        "data_quality_status": quality,
        "data_quality_detail": row.get("data_quality_detail", ""),
        "review_reason": row.get("review_reason", "") or row.get("data_quality_detail", ""),
        "target_date": row.get("target_date", ""),
        "target_product": row.get("target_product", ""),
        "target_country": row.get("target_country", ""),
        "target_metric": row.get("target_metric", ""),
        "tooltip_product": row.get("tooltip_product", ""),
        "tooltip_country": row.get("tooltip_country", ""),
        "tooltip_metric": row.get("tooltip_metric", ""),
        "tooltip_rank": row.get("tooltip_rank", ""),
        "data_origin": "today",
    }


def build_history_fallback_row(brand, country, history_row=None, queue_row=None):
    if history_row:
        stale = is_history_stale(history_row)
        return {
            "brand": brand,
            "package": APP_IDS.get(brand, ""),
            "country": country,
            "country_display": country_display_name(country),
            "market_tier": history_row.get("market_tier", "") or market_tier_for(country),
            "tooltip_date": history_row.get("tooltip_date", "") or history_row.get("date", ""),
            "app_name": "",
            "revenue_rank_tools": to_int(history_row.get("revenue_rank_tools")),
            "revenue_rank_apps": None,
            "top_free_rank_tools": None,
            "status": STALE_HISTORY if stale else HISTORY_FALLBACK,
            "status_detail": "数据超过14天未更新，需复核" if stale else "未完成今日抓取 / 使用最近一次数据",
            "error_message": "",
            "source_url": source_url(brand, country),
            "raw_tooltip_text": "",
            "screenshot_path": history_row.get("screenshot_path", ""),
            "latest_fetch_date": history_row.get("latest_fetch_date", "") or history_row.get("date", ""),
            "fetch_mode": history_row.get("fetch_mode", "") or "Historical",
            "data_quality_status": QUALITY_EXPIRED if stale else QUALITY_HISTORICAL,
            "data_quality_detail": "历史数据超过14天未更新" if stale else "本次未抓取，沿用最近一次已核验数据",
            "review_reason": "历史数据超过14天未更新" if stale else "",
            "target_date": "",
            "target_product": brand,
            "target_country": country,
            "target_metric": "",
            "tooltip_product": "",
            "tooltip_country": "",
            "tooltip_metric": "",
            "tooltip_rank": "",
            "data_origin": "history",
        }
    queue_status = (queue_row or {}).get("status", "")
    status = RATE_LIMITED if queue_status == RATE_LIMITED else PENDING_TODAY
    detail = "今日尚未抓取，等待队列继续"
    if queue_status == "FAILED":
        detail = "今日尚未完成，队列将在后续重试"
    elif queue_status == RATE_LIMITED:
        detail = "触发限流，等待后继续"
    return {
        "brand": brand,
        "package": APP_IDS.get(brand, ""),
        "country": country,
        "country_display": country_display_name(country),
        "market_tier": market_tier_for(country),
        "tooltip_date": "",
        "app_name": "",
        "revenue_rank_tools": None,
        "revenue_rank_apps": None,
        "top_free_rank_tools": None,
        "status": status,
        "status_detail": detail,
        "error_message": "",
        "source_url": source_url(brand, country),
        "raw_tooltip_text": "",
        "screenshot_path": "",
        "latest_fetch_date": "",
        "fetch_mode": "",
        "data_quality_status": "",
        "data_quality_detail": detail,
        "review_reason": "",
        "target_date": "",
        "target_product": brand,
        "target_country": country,
        "target_metric": "",
        "tooltip_product": "",
        "tooltip_country": "",
        "tooltip_metric": "",
        "tooltip_rank": "",
        "data_origin": "pending",
    }


def build_dashboard_data(days: int = DEFAULT_DAYS):
    strategy = load_monitor_strategy()
    latest_detail = get_latest_file(DETAIL_PATTERN)
    if not latest_detail:
        raise RuntimeError("No dated detail CSV found in output/.")

    detail_rows = read_csv_rows(latest_detail)
    latest_file_date = parse_date_from_filename(latest_detail)
    latest_file_date_str = latest_file_date.strftime("%Y-%m-%d") if latest_file_date else ""

    series_rows = load_recent_summary_records(days=days)
    queue_rows = read_queue_rows()
    queue_by_key = {(row.get("brand", ""), row.get("country", "")): row for row in queue_rows}
    history_by_key = latest_history_by_task(series_rows)

    today_by_key = {}
    for row in detail_rows:
        normalized = normalize_latest_detail_row(row, latest_file_date_str)
        today_by_key[(normalized["brand"], normalized["country"])] = normalized

    latest_rows = []
    for brand, country in configured_task_keys():
        key = (brand, country)
        if key in today_by_key:
            latest_rows.append(today_by_key[key])
        else:
            latest_rows.append(build_history_fallback_row(brand, country, history_by_key.get(key), queue_by_key.get(key)))

    for key, row in today_by_key.items():
        if key not in configured_task_keys():
            latest_rows.append(row)

    success_count = sum(1 for row in latest_rows if row["status"] == SUCCESS)
    partial_count = sum(1 for row in latest_rows if row["status"] == PARTIAL_SUCCESS)
    capture_failed_count = sum(
        1
        for row in latest_rows
        if row["status"] not in (SUCCESS, PARTIAL_SUCCESS, "DATA_NOT_VISIBLE")
        and row["status"] not in (HISTORY_FALLBACK, STALE_HISTORY, PENDING_TODAY)
    )
    review_count = sum(1 for row in latest_rows if needs_manual_review(row, latest_file_date_str))
    today_crawled_count = len(today_by_key)
    today_uncrawled_count = sum(1 for row in latest_rows if row.get("data_origin") in ("history", "pending"))
    history_fallback_count = sum(1 for row in latest_rows if row.get("data_origin") == "history")
    rate_limited_count = sum(1 for row in latest_rows if row.get("status") == RATE_LIMITED)
    stale_history_count = sum(1 for row in latest_rows if row.get("status") == STALE_HISTORY)
    queue_remaining_count = sum(1 for row in queue_rows if row.get("status") != "DONE")
    safe_limit_reached = bool(queue_rows and queue_remaining_count > 0)
    fetch_modes = [row.get("fetch_mode", "") for row in today_by_key.values() if row.get("fetch_mode")]
    if fetch_modes:
        current_fetch_mode = max(set(fetch_modes), key=fetch_modes.count)
    else:
        current_fetch_mode = fetch_mode_label(strategy.get("default_mode", "")) or "Daily Core"

    available_brands = {
        row["brand"]
        for row in latest_rows + series_rows
        if row.get("brand")
    }
    available_brands.update(BRAND_ORDER)
    brands = [brand for brand in BRAND_ORDER if brand in available_brands]
    brands += sorted(brand for brand in available_brands if brand not in brands)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_monitor_file_date": latest_file_date_str,
        "overview": {
            "success_count": success_count,
            "partial_count": partial_count,
            "capture_failed_count": capture_failed_count,
            "review_count": review_count,
            "today_crawled_count": today_crawled_count,
            "today_uncrawled_count": today_uncrawled_count,
            "history_fallback_count": history_fallback_count,
            "rate_limited_count": rate_limited_count,
            "stale_history_count": stale_history_count,
            "queue_remaining_count": queue_remaining_count,
            "safe_limit_reached": safe_limit_reached,
            "product_count": len(brands),
            "country_count": len(COUNTRY_ORDER),
            "latest_monitor_date": latest_file_date_str,
            "fetch_mode": current_fetch_mode,
            "stale_after_days": STALE_AFTER_DAYS,
        },
        "brands": ["ugphone", "ldcloud", "redfinger", "vsphone"],
        "countries": COUNTRY_ORDER,
        "country_names": MARKET_TIERS.get("country_names", {}),
        "market_tiers": MARKET_TIERS.get("tiers", {}),
        "latest_rows": latest_rows,
        "series_rows": series_rows,
    }


def render_dashboard_html(data: dict):
    payload = json.dumps(data, ensure_ascii=False)
    html = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Sensor Tower Multi-Product Dashboard</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {
      --bg:#f5f7fb; --card:#fff; --text:#172033; --muted:#647084; --line:#d9e2ef;
      --ok:#198754; --warn:#b86b00; --bad:#c92a2a; --accent:#0f6bff; --soft:#eef7f0;
    }
    body { margin:0; font-family:"Segoe UI","Microsoft YaHei",sans-serif; background:var(--bg); color:var(--text); }
    .wrap { max-width:1500px; margin:0 auto; padding:18px; }
    .head { display:flex; justify-content:space-between; gap:12px; align-items:flex-end; margin-bottom:14px; }
    .title { font-size:25px; font-weight:700; }
    .meta,.small { color:var(--muted); font-size:12px; }
    .cards { display:grid; grid-template-columns:repeat(8,minmax(120px,1fr)); gap:10px; }
    .card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px; }
    .card.review { cursor:pointer; border-color:#f0b35a; }
    .card.review.active { box-shadow:0 0 0 2px #f0b35a inset; }
    .k { font-size:12px; color:var(--muted); }
    .v { font-size:24px; font-weight:700; margin-top:6px; }
    .panel { margin-top:12px; background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px; }
    .banner { display:none; margin-top:12px; border:1px solid #f0b35a; background:#fff7e8; color:#8a5200; border-radius:8px; padding:10px 12px; font-weight:700; }
    .panel h3 { margin:0 0 10px; font-size:16px; }
    .filters { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:10px; }
    select,button { border:1px solid var(--line); background:#fff; padding:6px 10px; border-radius:6px; }
    button.on { background:var(--accent); color:#fff; border-color:var(--accent); }
    .trendGrid { display:grid; grid-template-columns: minmax(0,2fr) minmax(420px,1fr); gap:12px; align-items:start; }
    table { width:100%; border-collapse:collapse; font-size:13px; }
    th,td { border:1px solid var(--line); padding:7px; text-align:left; vertical-align:top; }
    th { background:#f1f5fa; }
    tr.ug-core { background:var(--soft); }
    .status-SUCCESS { color:var(--ok); font-weight:700; }
    .status-PARTIAL_SUCCESS,.status-TOOLTIP_PARSE_FAILED,.status-RANK_CAPTURE_FAILED { color:var(--warn); font-weight:700; }
    .status-FAILED,.status-PAGE_LOAD_FAILED,.status-CHART_NOT_FOUND,.status-TOOLTIP_NOT_FOUND,.status-RANK_TEXT_NOT_PARSED { color:var(--bad); font-weight:700; }
    .status-DATA_NOT_VISIBLE { color:var(--muted); font-weight:700; }
    .status-HISTORY_FALLBACK,.status-PENDING_TODAY { color:var(--warn); font-weight:700; }
    .status-RATE_LIMITED { color:var(--bad); font-weight:700; }
    a.reviewLink { color:var(--accent); font-weight:700; text-decoration:none; }
    @media (max-width:1100px) { .cards { grid-template-columns:repeat(2,1fr); } .trendGrid { grid-template-columns:1fr; } }
  </style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div>
      <div class="title">Sensor Tower Multi-Product Dashboard</div>
      <div class="small">Latest monitor date: <span id="latestDate"></span></div>
    </div>
    <div class="meta">Generated: <span id="generatedAt"></span></div>
  </div>

  <div class="cards">
    <div class="card"><div class="k">今日已抓取</div><div class="v" id="todayCrawledCount"></div></div>
    <div class="card"><div class="k">今日未抓取</div><div class="v" id="todayUncrawledCount"></div></div>
    <div class="card"><div class="k">使用历史数据</div><div class="v" id="historyFallbackCount"></div></div>
    <div class="card"><div class="k">抓取失败</div><div class="v" id="captureFailedCount"></div></div>
    <div class="card"><div class="k">触发限流</div><div class="v" id="rateLimitedCount"></div></div>
    <div class="card review" id="reviewCard"><div class="k">需人工复核</div><div class="v" id="reviewCount"></div></div>
    <div class="card"><div class="k">产品数</div><div class="v" id="productCount"></div></div>
    <div class="card"><div class="k">国家数</div><div class="v" id="countryCount"></div></div>
  </div>
  <div class="banner" id="limitBanner"></div>

  <div class="panel">
    <h3>Trend</h3>
    <div class="filters">
      <label>Brand</label><select id="brandFilter"></select>
      <label>Country</label><select id="countryFilter"></select>
      <label>Metric</label>
      <button class="metricBtn on" data-metric="revenue_rank_tools">Tools</button>
      <button class="metricBtn" data-metric="revenue_rank_apps">Apps</button>
      <button class="metricBtn" data-metric="top_free_rank_tools">Free</button>
      <label>Date Range</label><select id="rangeFilter"><option value="7">最近7天</option><option value="30">最近30天</option></select>
    </div>
    <div class="trendGrid">
      <div id="trendChart" style="height:400px;"></div>
      <div>
        <h3>关键波动榜</h3>
        <div id="volatilityTable"></div>
      </div>
    </div>
  </div>

  <div class="panel">
    <h3>重点市场判断</h3>
    <div id="marketTable"></div>
  </div>

  <div class="panel">
    <h3>Country Comparison (Latest)</h3>
    <div id="countryTable"></div>
  </div>

  <div class="panel">
    <h3>异常与提醒</h3>
    <div id="alertTable"></div>
  </div>
</div>

<script>
const DATA = __PAYLOAD__;
const BRAND_ORDER = ["ugphone","ldcloud","redfinger","vsphone"];
const METRICS = [
  ["revenue_rank_tools", "Tools"],
  ["revenue_rank_apps", "Apps"],
  ["top_free_rank_tools", "Free"]
];
let currentMetric = "revenue_rank_tools";
let reviewOnly = false;

function byId(id) { return document.getElementById(id); }
function n(v) { return (v === null || v === undefined || v === "") ? null : Number(v); }
function fmt(v) { return n(v) === null ? "-" : `#${v}`; }
function hasRank(row) { return METRICS.some(([key]) => n(row[key]) !== null); }
function validRank(row) { return Boolean(row.tooltip_date) && hasRank(row); }
function isReview(row) { return row.status === "PARTIAL_SUCCESS" || ["TOOLTIP_PARSE_FAILED","RANK_CAPTURE_FAILED","RATE_LIMITED"].includes(row.status) || !["SUCCESS","PARTIAL_SUCCESS","DATA_NOT_VISIBLE","HISTORY_FALLBACK","PENDING_TODAY"].includes(row.status); }
function statusLabel(status) {
  const labels = {
    SUCCESS: "成功",
    PARTIAL_SUCCESS: "部分成功，需复核",
    TOOLTIP_PARSE_FAILED: "抓取失败，需复核",
    RANK_CAPTURE_FAILED: "抓取失败，需复核",
    DATA_NOT_VISIBLE: "页面无可见排名",
    HISTORY_FALLBACK: "未完成今日抓取 / 使用最近一次数据",
    PENDING_TODAY: "今日尚未抓取",
    RATE_LIMITED: "触发限流，等待后继续",
    FAILED: "失败"
  };
  return labels[status] || status || "失败";
}
function brandSort(a, b) {
  const ai = BRAND_ORDER.indexOf(a), bi = BRAND_ORDER.indexOf(b);
  return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi) || a.localeCompare(b);
}
function rankSortValue(row) {
  for (const key of ["revenue_rank_tools", "revenue_rank_apps", "top_free_rank_tools"]) {
    const value = n(row[key]);
    if (value !== null) return value;
  }
  return 999999;
}
function bestMetric(row) {
  const vals = METRICS.map(([key,label]) => ({ key, label, value:n(row[key]) })).filter(x => x.value !== null);
  vals.sort((a,b) => a.value - b.value);
  return vals[0] || { label:"-", value:null };
}
function marketLevel(rank) {
  if (rank === null) return "低优先级/待复核";
  if (rank <= 50) return "核心市场";
  if (rank <= 150) return "潜力市场";
  if (rank <= 300) return "观察市场";
  return "低优先级/待复核";
}
function sourceCell(row) {
  if (!validRank(row) || !row.source_url) return "-";
  return `<a class="reviewLink" href="${row.source_url}" target="_blank" rel="noopener noreferrer">Review</a>`;
}
function latestRows() {
  const b = byId("brandFilter").value;
  const c = byId("countryFilter").value;
  return DATA.latest_rows.filter(row => (b === "ALL" || row.brand === b) && (c === "ALL" || row.country === c) && (!reviewOnly || isReview(row)));
}
function seriesRows() {
  const b = byId("brandFilter").value;
  const c = byId("countryFilter").value;
  const range = Number(byId("rangeFilter").value);
  const dates = [...new Set(DATA.series_rows.map(row => row.date))].sort().slice(-range);
  return DATA.series_rows.filter(row => dates.includes(row.date) && (b === "ALL" || row.brand === b) && (c === "ALL" || row.country === c));
}

function init() {
  byId("generatedAt").textContent = DATA.generated_at;
  byId("latestDate").textContent = DATA.overview.latest_monitor_date;
  byId("todayCrawledCount").textContent = DATA.overview.today_crawled_count;
  byId("todayUncrawledCount").textContent = DATA.overview.today_uncrawled_count;
  byId("historyFallbackCount").textContent = DATA.overview.history_fallback_count;
  byId("captureFailedCount").textContent = DATA.overview.capture_failed_count;
  byId("rateLimitedCount").textContent = DATA.overview.rate_limited_count;
  byId("reviewCount").textContent = DATA.overview.review_count;
  byId("productCount").textContent = DATA.overview.product_count;
  byId("countryCount").textContent = DATA.overview.country_count;
  if (DATA.overview.safe_limit_reached) {
    byId("limitBanner").style.display = "block";
    byId("limitBanner").textContent = `今日安全抓取额度已用完，剩余 ${DATA.overview.queue_remaining_count} 个任务将在下次运行继续。`;
  }

  const brandOptions = ["ALL", ...DATA.brands].sort((a,b) => a === "ALL" ? -1 : b === "ALL" ? 1 : brandSort(a,b));
  byId("brandFilter").innerHTML = brandOptions.map(brand => `<option value="${brand}">${brand}</option>`).join("");
  byId("brandFilter").value = brandOptions.includes("ugphone") ? "ugphone" : brandOptions[0];
  byId("countryFilter").innerHTML = ["ALL", ...DATA.countries].map(country => `<option value="${country}">${country}</option>`).join("");

  ["brandFilter","countryFilter","rangeFilter"].forEach(id => byId(id).onchange = renderAll);
  document.querySelectorAll(".metricBtn").forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll(".metricBtn").forEach(item => item.classList.remove("on"));
      btn.classList.add("on");
      currentMetric = btn.dataset.metric;
      renderAll();
    };
  });
  byId("reviewCard").onclick = () => {
    reviewOnly = !reviewOnly;
    byId("reviewCard").classList.toggle("active", reviewOnly);
    renderAll();
  };
}

function renderTrend() {
  const groups = {};
  seriesRows().forEach(row => {
    const value = n(row[currentMetric]);
    if (value === null) return;
    const key = byId("brandFilter").value === "ALL" ? `${row.brand} | ${row.country}` : row.country;
    if (!groups[key]) groups[key] = [];
    groups[key].push({ x: row.date, y: value });
  });
  const traces = Object.entries(groups).map(([name, vals]) => {
    vals.sort((a,b) => a.x.localeCompare(b.x));
    return { x: vals.map(v => v.x), y: vals.map(v => v.y), mode:"lines+markers", name };
  });
  Plotly.newPlot("trendChart", traces, {
    margin:{l:52,r:20,t:8,b:38},
    yaxis:{title:"Rank", autorange:"reversed"},
    xaxis:{title:"Date"},
    legend:{orientation:"h"}
  }, { displayModeBar:false, responsive:true });
}

function renderVolatility() {
  const rows = seriesRows();
  const grouped = {};
  rows.forEach(row => {
    METRICS.forEach(([key,label]) => {
      const value = n(row[key]);
      if (value === null || !row.tooltip_date) return;
      const id = `${row.brand}|${row.country}|${label}`;
      if (!grouped[id]) grouped[id] = [];
      grouped[id].push({ ...row, metric:label, value });
    });
  });
  const lines = Object.values(grouped).map(vals => {
    vals.sort((a,b) => a.date.localeCompare(b.date));
    if (vals.length < 2) return null;
    const latest = vals[vals.length - 1], previous = vals[vals.length - 2];
    const delta = previous.value - latest.value;
    return { brand:latest.brand, country:latest.country, metric:latest.metric, latest:latest.value, previous:previous.value, delta };
  }).filter(Boolean).sort((a,b) => Math.abs(b.delta) - Math.abs(a.delta)).slice(0, 12);

  let html = "<table><thead><tr><th>Brand</th><th>Country</th><th>Metric</th><th>Latest Rank</th><th>Previous Rank</th><th>Change</th><th>Change Type</th></tr></thead><tbody>";
  lines.forEach(row => {
    const arrow = row.delta > 0 ? "↑" : row.delta < 0 ? "↓" : "-";
    const type = row.delta > 0 ? "排名上升" : row.delta < 0 ? "排名下降" : "持平";
    html += `<tr><td>${row.brand}</td><td>${row.country}</td><td>${row.metric}</td><td>${fmt(row.latest)}</td><td>${fmt(row.previous)}</td><td>${arrow} ${row.delta > 0 ? "+" : ""}${row.delta}</td><td>${type}</td></tr>`;
  });
  html += "</tbody></table>";
  byId("volatilityTable").innerHTML = lines.length ? html : "<div class='small'>历史数据不足，暂无法计算波动。</div>";
}

function renderMarketTable() {
  const rows = latestRows().slice().sort((a,b) => brandSort(a.brand,b.brand) || rankSortValue(a) - rankSortValue(b) || a.country.localeCompare(b.country));
  let html = "<table><thead><tr><th>Brand</th><th>Country</th><th>Market Level</th><th>Tooltip Date</th><th>Tools</th><th>Apps</th><th>Free</th><th>Status</th><th>Source Link</th></tr></thead><tbody>";
  rows.forEach(row => {
    const best = validRank(row) ? bestMetric(row) : { label:"-", value:null };
    const cls = row.brand === "ugphone" && best.value !== null && best.value <= 50 ? " class='ug-core'" : "";
    html += `<tr${cls}><td>${row.brand}</td><td>${row.country}</td><td>${marketLevel(best.value)}</td><td>${row.tooltip_date || "-"}</td><td>${fmt(row.revenue_rank_tools)}</td><td>${fmt(row.revenue_rank_apps)}</td><td>${fmt(row.top_free_rank_tools)}</td><td class="status-${row.status}">${statusLabel(row.status)}</td><td>${sourceCell(row)}</td></tr>`;
  });
  html += "</tbody></table>";
  byId("marketTable").innerHTML = html;
}

function renderCountryTable() {
  const rows = latestRows();
  const brands = [...new Set(rows.map(row => row.brand))].sort(brandSort);
  const countries = [...new Set(rows.map(row => row.country))];
  const lines = countries.map(country => {
    const sub = rows.filter(row => row.country === country);
    const ranks = {};
    brands.forEach(brand => {
      const row = sub.find(item => item.brand === brand);
      ranks[brand] = row && validRank(row) ? n(row[currentMetric]) : null;
    });
    const valid = Object.entries(ranks).filter(([,value]) => value !== null);
    valid.sort((a,b) => a[1] - b[1]);
    const leader = valid[0] || ["", null];
    const ug = ranks.ugphone;
    return { country, ranks, leaderBrand:leader[0], leaderRank:leader[1], sortRank:ug !== null ? ug : (leader[1] ?? 999999) };
  }).sort((a,b) => a.sortRank - b.sortRank || a.country.localeCompare(b.country));

  let html = "<table><thead><tr><th>Country</th>";
  brands.forEach(brand => html += `<th>${brand}</th>`);
  html += "<th>Leader</th><th>Gap vs Leader</th></tr></thead><tbody>";
  lines.forEach(row => {
    const gaps = Object.entries(row.ranks).filter(([,value]) => value !== null && row.leaderRank !== null).map(([brand,value]) => `${brand}:${value - row.leaderRank >= 0 ? "+" : ""}${value - row.leaderRank}`).join(" | ");
    html += `<tr><td>${row.country}</td>`;
    brands.forEach(brand => html += `<td>${fmt(row.ranks[brand])}</td>`);
    html += `<td>${row.leaderBrand ? `${row.leaderBrand} (${fmt(row.leaderRank)})` : "-"}</td><td>${gaps || "-"}</td></tr>`;
  });
  html += "</tbody></table>";
  byId("countryTable").innerHTML = html;
}

function renderAlerts() {
  const rows = DATA.latest_rows.filter(isReview);
  if (!rows.length) {
    byId("alertTable").innerHTML = "<div class='small'>暂无需要复核的数据。</div>";
    return;
  }
  let html = "<table><thead><tr><th>Brand</th><th>Country</th><th>Tooltip Date</th><th>Status</th><th>Status Detail / Error</th><th>Raw Tooltip</th><th>Source Link</th></tr></thead><tbody>";
  rows.forEach(row => {
    html += `<tr><td>${row.brand}</td><td>${row.country}</td><td>${row.tooltip_date || "-"}</td><td class="status-${row.status}">${statusLabel(row.status)}</td><td>${row.status_detail || row.error_message || "-"}</td><td>${row.raw_tooltip_text || "-"}</td><td>${row.source_url ? `<a class="reviewLink" href="${row.source_url}" target="_blank" rel="noopener noreferrer">Review</a>` : "-"}</td></tr>`;
  });
  html += "</tbody></table>";
  byId("alertTable").innerHTML = html;
}

function renderAll() {
  renderTrend();
  renderVolatility();
  renderMarketTable();
  renderCountryTable();
  renderAlerts();
}

init();
renderAll();
</script>
</body>
</html>
"""
    return html.replace("__PAYLOAD__", payload)


def build_dashboard(days: int = DEFAULT_DAYS):
    data = build_dashboard_data(days=days)
    from dashboard_theme import render_dashboard_html as render_dashboard_html_v2

    html = render_dashboard_html_v2(data)
    output_html = os.path.join(OUTPUT_DIR, "dashboard.html")
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(BASE_DIR, "dashboard.html"), "w", encoding="utf-8") as f:
        f.write(html)
    return output_html


if __name__ == "__main__":
    path = build_dashboard(days=DEFAULT_DAYS)
    print(f"[OK] Dashboard generated: {path}")


