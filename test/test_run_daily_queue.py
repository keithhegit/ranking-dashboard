import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "linux" / "run_daily_queue.py"
spec = importlib.util.spec_from_file_location("run_daily_queue", MODULE_PATH)
queue = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = queue
spec.loader.exec_module(queue)


def write_detail(path, rows):
    fields = list(queue.DETAIL_FIELDS)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


class RunDailyQueueTest(unittest.TestCase):
    def test_merge_keeps_ranked_success_when_later_batch_is_rate_limited(self):
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp)
            write_detail(
                batch_dir / "detail_001_ugphone_US.csv",
                [
                    {
                        "brand": "ugphone",
                        "country": "US",
                        "revenue_rank_tools": "383",
                        "status": "PARTIAL_SUCCESS",
                        "batch_file": "old",
                    }
                ],
            )
            write_detail(
                batch_dir / "detail_002_ugphone_US.csv",
                [
                    {
                        "brand": "ugphone",
                        "country": "US",
                        "revenue_rank_tools": "",
                        "status": "RATE_LIMITED",
                        "batch_file": "new",
                    }
                ],
            )

            merged = queue.merge_detail_files(batch_dir, ["ugphone"], ["US"], "20260616", "2026-06-16")

        self.assertEqual(merged[0]["revenue_rank_tools"], "383")
        self.assertEqual(merged[0]["status"], "PARTIAL_SUCCESS")

    def test_no_category_markets_are_written_without_scraping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "output").mkdir()
            (root / "config" / "no_category_ranking_data.json").write_text(
                json.dumps({"pairs": [{"brand": "vsphone", "country": "US"}]}),
                encoding="utf-8",
            )
            runner = queue.DailyQueueRunner(
                root=root,
                date_raw="20260616",
                date_iso="2026-06-16",
                products=["vsphone"],
                countries=["US"],
                dry_run=True,
            )

            result = runner.run()

            self.assertEqual(result["no_category_data"], 1)
            detail = root / "output" / "sensor_tower_multi_product_multi_country_20260616.csv"
            with detail.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]["status"], "NO_CATEGORY_RANKING_DATA")
            self.assertIn("no available category ranking", rows[0]["status_detail"])

    def test_first_rate_limited_result_sets_cooldown_and_stops_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "output").mkdir()
            calls = []

            def fake_collect(task, detail_path):
                calls.append((task.brand, task.country))
                write_detail(
                    detail_path,
                    [
                        {
                            "brand": task.brand,
                            "country": task.country,
                            "status": "RATE_LIMITED",
                            "status_detail": "HTTP 429 Too Many Requests",
                        }
                    ],
                )
                return 0

            runner = queue.DailyQueueRunner(
                root=root,
                date_raw="20260616",
                date_iso="2026-06-16",
                products=["ugphone"],
                countries=["US", "JP"],
                collect_one=fake_collect,
                sleep=lambda seconds: None,
                now=lambda: 1000.0,
                success_sleep_range=(0, 0),
                cooldown_after_successes=99,
                hard_cooldown_range=(0, 0),
                rate_limit_cooldown_seconds=1800,
            )

            result = runner.run()

            self.assertEqual(calls, [("ugphone", "US")])
            self.assertEqual(result["rate_limited"], 1)
            self.assertEqual(result["stopped_for_rate_limit"], 1)
            state = json.loads((root / "output" / "daily_queue_20260616" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["cooldown_until_epoch"], 2800.0)

    def test_success_cache_skips_same_day_scrape_on_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            batch_dir = root / "output" / "daily_queue_20260616"
            batch_dir.mkdir(parents=True)
            write_detail(
                batch_dir / "detail_001_ugphone_US.csv",
                [
                    {
                        "brand": "ugphone",
                        "country": "US",
                        "revenue_rank_tools": "383",
                        "status": "PARTIAL_SUCCESS",
                    }
                ],
            )
            calls = []

            def fake_collect(task, detail_path):
                calls.append((task.brand, task.country))
                return 0

            runner = queue.DailyQueueRunner(
                root=root,
                date_raw="20260616",
                date_iso="2026-06-16",
                products=["ugphone"],
                countries=["US"],
                collect_one=fake_collect,
                sleep=lambda seconds: None,
                success_sleep_range=(0, 0),
            )

            result = runner.run()

            self.assertEqual(calls, [])
            self.assertEqual(result["skipped_cached"], 1)


if __name__ == "__main__":
    unittest.main()
