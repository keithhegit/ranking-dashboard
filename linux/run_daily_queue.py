#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import random
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


PRODUCTS = ["ugphone", "ldcloud", "redfinger", "vsphone"]
COUNTRIES = ["TH", "VN", "PH", "BR", "TR", "MY", "ID", "HK", "TW", "KR", "US", "MX", "SG", "JP", "PL", "DE", "GB", "IN", "IT", "FR"]
PRODUCT_PACKAGES = {
    "ugphone": "com.tykeji.ugphone",
    "ldcloud": "com.ld.cph.gl",
    "vsphone": "com.vsphone.overseas",
    "redfinger": "com.redfinger.global",
}
DETAIL_FIELDS = [
    "brand",
    "package",
    "country",
    "tooltip_date",
    "app_name",
    "revenue_rank_tools",
    "revenue_rank_apps",
    "top_free_rank_tools",
    "source_url",
    "crawl_time",
    "status",
    "status_detail",
    "error_message",
    "candidate_tooltip_dates",
    "candidate_count",
    "selected_tooltip_date",
    "page_loaded_screenshot",
    "final_hover_screenshot",
    "retry_count",
    "screenshot_path",
    "selected_candidate_index",
    "selected_candidate_raw_text",
    "raw_tooltip_text",
    "selected_candidate_x",
    "selected_candidate_y",
    "all_candidates_json",
    "batch_file",
]

SUMMARY_FIELDS = ["brand", "country", "tooltip_date", "revenue_rank_tools", "status", "status_detail", "batch_file"]
TERMINAL_NO_SCRAPE_STATUSES = {"NO_CATEGORY_RANKING_DATA"}
SUCCESS_STATUSES = {"SUCCESS", "PARTIAL_SUCCESS"}
RATE_LIMIT_STATUSES = {"RATE_LIMITED"}


@dataclass(frozen=True)
class Task:
    index: int
    brand: str
    country: str

    @property
    def name(self) -> str:
        return f"{self.index:03d}_{self.brand}_{self.country}"


def parse_csv(value: str | None, default: list[str], transform: Callable[[str], str] = lambda item: item) -> list[str]:
    items = [transform(item.strip()) for item in str(value or "").split(",") if item.strip()]
    return items or list(default)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, fields: Iterable[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in writer.fieldnames})


def row_priority(row: dict[str, str]) -> int:
    rank = str(row.get("revenue_rank_tools", "")).strip()
    status = str(row.get("status", "")).upper()
    if rank.isdigit():
        return 100_000_000 - int(rank)
    if status in SUCCESS_STATUSES:
        return 80_000_000
    if status in TERMINAL_NO_SCRAPE_STATUSES:
        return 70_000_000
    if status in {"RANK_CAPTURE_FAILED", "TOOLTIP_PARSE_FAILED", "CHART_NOT_FOUND", "TOOLTIP_NOT_FOUND", "RANK_TEXT_NOT_PARSED"}:
        return 30_000_000
    if status in RATE_LIMIT_STATUSES:
        return 10_000_000
    if status == "PENDING_TODAY":
        return 1_000_000
    return 0


def is_cached_terminal(row: dict[str, str] | None) -> bool:
    if not row:
        return False
    status = str(row.get("status", "")).upper()
    rank = str(row.get("revenue_rank_tools", "")).strip()
    return rank.isdigit() or status in SUCCESS_STATUSES or status in TERMINAL_NO_SCRAPE_STATUSES


def is_rate_limited(row: dict[str, str] | None) -> bool:
    if not row:
        return False
    status = str(row.get("status", "")).upper()
    detail = str(row.get("status_detail", "")).lower()
    error = str(row.get("error_message", "")).lower()
    return status in RATE_LIMIT_STATUSES or "429" in detail or "rate limit" in detail or "429" in error or "rate limit" in error


def load_no_category_pairs(root: Path) -> set[tuple[str, str]]:
    path = root / "config" / "no_category_ranking_data.json"
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs = data.get("pairs", []) if isinstance(data, dict) else data
    return {
        (str(item.get("brand", "")).lower(), str(item.get("country", "")).upper())
        for item in pairs
        if item.get("brand") and item.get("country")
    }


def best_rows_from_detail_files(batch_dir: Path) -> dict[tuple[str, str], dict[str, str]]:
    best: dict[tuple[str, str], dict[str, str]] = {}
    for path in sorted(batch_dir.glob("detail_*.csv")):
        for row in read_csv_rows(path):
            brand = str(row.get("brand", "")).lower()
            country = str(row.get("country", "")).upper()
            if not brand or not country:
                continue
            row = dict(row)
            row["brand"] = brand
            row["country"] = country
            row["batch_file"] = row.get("batch_file") or path.name
            key = (brand, country)
            if key not in best or row_priority(row) > row_priority(best[key]):
                best[key] = row
    return best


def merge_detail_files(batch_dir: Path, products: list[str], countries: list[str], date_raw: str, date_iso: str) -> list[dict[str, str]]:
    best = best_rows_from_detail_files(batch_dir)
    rows: list[dict[str, str]] = []
    for brand in products:
        for country in countries:
            row = dict(best.get((brand, country), {}))
            if not row:
                row = {
                    "brand": brand,
                    "package": PRODUCT_PACKAGES.get(brand, ""),
                    "country": country,
                    "tooltip_date": "",
                    "app_name": "",
                    "revenue_rank_tools": "",
                    "source_url": "",
                    "crawl_time": date_iso,
                    "status": "PENDING_TODAY",
                    "status_detail": "not collected yet",
                }
            row["brand"] = brand
            row["country"] = country
            row["package"] = row.get("package") or PRODUCT_PACKAGES.get(brand, "")
            row["revenue_rank_apps"] = ""
            row["top_free_rank_tools"] = ""
            rows.append({field: row.get(field, "") for field in DETAIL_FIELDS})
    return rows


def write_no_category_detail(path: Path, task: Task, date_iso: str) -> None:
    row = {
        "brand": task.brand,
        "package": PRODUCT_PACKAGES.get(task.brand, ""),
        "country": task.country,
        "tooltip_date": "",
        "app_name": task.brand,
        "revenue_rank_tools": "",
        "source_url": f"https://app.sensortower.com/overview/{PRODUCT_PACKAGES.get(task.brand, '')}?country={task.country}&tab=category_rankings",
        "crawl_time": date_iso,
        "status": "NO_CATEGORY_RANKING_DATA",
        "status_detail": "Sensor Tower page shows no available category ranking data for this market",
        "batch_file": path.name,
    }
    write_rows(path, DETAIL_FIELDS, [row])


class DailyQueueRunner:
    def __init__(
        self,
        root: Path,
        date_raw: str,
        date_iso: str,
        products: list[str] | None = None,
        countries: list[str] | None = None,
        collect_one: Callable[[Task, Path], int] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.time,
        dry_run: bool = False,
        success_sleep_range: tuple[float, float] = (45.0, 120.0),
        cooldown_after_successes: int = 10,
        hard_cooldown_range: tuple[float, float] = (600.0, 1200.0),
        rate_limit_cooldown_seconds: float = 3600.0,
    ):
        self.root = root
        self.date_raw = date_raw
        self.date_iso = date_iso
        self.products = products or PRODUCTS
        self.countries = countries or COUNTRIES
        self.collect_one = collect_one or self.collect_one_subprocess
        self.sleep = sleep
        self.now = now
        self.dry_run = dry_run
        self.success_sleep_range = success_sleep_range
        self.cooldown_after_successes = cooldown_after_successes
        self.hard_cooldown_range = hard_cooldown_range
        self.rate_limit_cooldown_seconds = rate_limit_cooldown_seconds
        self.output_dir = self.root / "output"
        self.batch_dir = self.output_dir / f"daily_queue_{self.date_raw}"
        self.state_path = self.batch_dir / "state.json"
        self.detail_out = self.output_dir / f"sensor_tower_multi_product_multi_country_{self.date_raw}.csv"
        self.summary_out = self.output_dir / f"sensor_tower_multi_product_summary_{self.date_raw}.csv"
        self.batch_dir.mkdir(parents=True, exist_ok=True)

    def read_state(self) -> dict:
        if not self.state_path.exists():
            return {}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def write_state(self, updates: dict) -> None:
        state = self.read_state()
        state.update(updates)
        state["updated_at_epoch"] = self.now()
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def active_cooldown(self) -> bool:
        until = float(self.read_state().get("cooldown_until_epoch", 0) or 0)
        return until > self.now()

    def detail_path_for(self, task: Task) -> Path:
        return self.batch_dir / f"detail_{task.name}.csv"

    def collect_one_subprocess(self, task: Task, detail_path: Path) -> int:
        python = os.environ.get("PYTHON", str(self.root / ".venv" / "bin" / "python"))
        timeout_bin = os.environ.get("TIMEOUT_BIN", "timeout")
        timeout_seconds = os.environ.get("BATCH_TIMEOUT_SECONDS", "600")
        current_detail = self.output_dir / f"sensor_tower_multi_product_multi_country_{self.date_raw}.csv"
        current_summary = self.output_dir / f"sensor_tower_multi_product_summary_{self.date_raw}.csv"
        current_detail.unlink(missing_ok=True)
        current_summary.unlink(missing_ok=True)
        stdout = self.batch_dir / f"run_{task.name}.out.log"
        stderr = self.batch_dir / f"run_{task.name}.err.log"
        env = dict(os.environ)
        env["ST_PRODUCTS"] = task.brand
        env["ST_COUNTRIES"] = task.country
        cmd = [timeout_bin, str(timeout_seconds), python, str(self.root / "sensor_tower_focus_fast.py")]
        with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
            code = subprocess.run(cmd, cwd=self.root, env=env, stdout=out, stderr=err, check=False).returncode
        if current_detail.exists():
            shutil.copy2(current_detail, detail_path)
        return code

    def throttle_after_success(self, success_count: int) -> None:
        if self.dry_run:
            return
        if self.cooldown_after_successes > 0 and success_count % self.cooldown_after_successes == 0:
            seconds = random.uniform(*self.hard_cooldown_range)
        else:
            seconds = random.uniform(*self.success_sleep_range)
        if seconds > 0:
            self.sleep(seconds)

    def run(self) -> dict[str, int]:
        no_category_pairs = load_no_category_pairs(self.root)
        existing = best_rows_from_detail_files(self.batch_dir)
        result = {
            "planned_tasks": len(self.products) * len(self.countries),
            "skipped_cached": 0,
            "no_category_data": 0,
            "collected": 0,
            "rate_limited": 0,
            "stopped_for_rate_limit": 0,
            "cooldown_active": 0,
        }
        success_count = 0

        for index, (brand, country) in enumerate(((brand, country) for brand in self.products for country in self.countries), start=1):
            task = Task(index=index, brand=brand, country=country)
            cached = existing.get((brand, country))
            if is_cached_terminal(cached):
                result["skipped_cached"] += 1
                continue

            detail_path = self.detail_path_for(task)
            if (brand, country) in no_category_pairs:
                write_no_category_detail(detail_path, task, self.date_iso)
                existing[(brand, country)] = read_csv_rows(detail_path)[0]
                result["no_category_data"] += 1
                continue

            if self.active_cooldown():
                result["cooldown_active"] = 1
                break

            if self.dry_run:
                continue

            self.collect_one(task, detail_path)
            rows = read_csv_rows(detail_path)
            latest = rows[0] if rows else None
            if is_rate_limited(latest):
                result["rate_limited"] += 1
                result["stopped_for_rate_limit"] = 1
                self.write_state(
                    {
                        "cooldown_until_epoch": self.now() + self.rate_limit_cooldown_seconds,
                        "cooldown_seconds": self.rate_limit_cooldown_seconds,
                        "cooldown_reason": "sensor_tower_rate_limited",
                        "first_rate_limited_task": {"brand": brand, "country": country},
                    }
                )
                break
            result["collected"] += 1
            if is_cached_terminal(latest):
                success_count += 1
                self.throttle_after_success(success_count)

        merged = merge_detail_files(self.batch_dir, self.products, self.countries, self.date_raw, self.date_iso)
        write_rows(self.detail_out, DETAIL_FIELDS, merged)
        write_rows(self.summary_out, SUMMARY_FIELDS, [{field: row.get(field, "") for field in SUMMARY_FIELDS} for row in merged])
        result["merged_rows"] = len(merged)
        self.write_state({"last_result": result})
        return result


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    date_raw = os.environ.get("DATE") or time.strftime("%Y%m%d")
    date_iso = os.environ.get("DATE_ISO") or f"{date_raw[0:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
    products = parse_csv(os.environ.get("PRODUCTS"), PRODUCTS, str.lower)
    countries = parse_csv(os.environ.get("COUNTRIES"), COUNTRIES, str.upper)
    runner = DailyQueueRunner(
        root=root,
        date_raw=date_raw,
        date_iso=date_iso,
        products=products,
        countries=countries,
        dry_run=os.environ.get("QUEUE_DRY_RUN", "0") == "1",
        success_sleep_range=(float(os.environ.get("SUCCESS_SLEEP_MIN", "45")), float(os.environ.get("SUCCESS_SLEEP_MAX", "120"))),
        cooldown_after_successes=int(os.environ.get("COOLDOWN_AFTER_SUCCESSES", "10")),
        hard_cooldown_range=(float(os.environ.get("HARD_COOLDOWN_MIN", "600")), float(os.environ.get("HARD_COOLDOWN_MAX", "1200"))),
        rate_limit_cooldown_seconds=float(os.environ.get("RATE_LIMIT_COOLDOWN_SECONDS", "3600")),
    )
    result = runner.run()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
