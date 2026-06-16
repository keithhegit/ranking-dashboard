import importlib.machinery
import importlib.util
import os
import re
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYC_PATH = os.path.join(
    BASE_DIR,
    "engine",
    "sensor_tower_multi_product_multi_country_20260428.pyc",
)

PRODUCT_MAP = {
    "ugphone": "com.tykeji.ugphone",
    "ldcloud": "com.ld.cph.gl",
    "vsphone": "com.vsphone.overseas",
    "redfinger": "com.redfinger.global",
}

DEFAULT_COUNTRIES = ["TH", "VN", "PH", "BR", "TR", "MY", "ID", "HK"]


def parse_csv_env(name, default):
    raw = os.environ.get(name, "")
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or default


def load_snapshot_module():
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError("This release requires Python 3.13 because its scraper engine is compiled for CPython 3.13.")
    if not os.path.exists(PYC_PATH):
        raise RuntimeError(f"Scraper engine not found: {PYC_PATH}")
    loader = importlib.machinery.SourcelessFileLoader("st_snapshot_release", PYC_PATH)
    spec = importlib.util.spec_from_loader("st_snapshot_release", loader)
    if spec is None:
        raise RuntimeError("Failed to load scraper engine")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def set_if_present(module, name, value):
    if hasattr(module, name):
        setattr(module, name, value)


def build_tooltip_reader_script():
    return r"""
    () => {
      const out = [];
      const seen = new Set();
      const tooltipTextPattern = /(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|#\s*[0-9,]+|Revenue|Grossing|\u6536\u5165\u6392\u884c)/;
      const selectors = [
        '[class*="TooltipChartRankings-module__tooltipCardContent"]',
        '[class*="TooltipChartValues-module__tooltipCardContent"]',
        '[class*="TooltipChartValues-module__tooltipCard"]',
        '.highcharts-tooltip',
        'g.highcharts-tooltip',
        '.highcharts-label.highcharts-tooltip',
        '[role="tooltip"]',
        '.echarts-tooltip',
        '.recharts-tooltip-wrapper',
        '.tippy-box',
        'div[class*="tooltip"]',
        'div[class*="Tooltip"]'
      ];
      const add = (selector, node) => {
        if (!node || seen.has(node)) return;
        seen.add(node);
        const rect = node.getBoundingClientRect();
        const style = window.getComputedStyle(node);
        const text = (node.innerText || node.textContent || '').trim();
        const html = node.innerHTML || node.outerHTML || '';
        const visible = rect && rect.width > 0 && rect.height > 0
          && style.display !== 'none'
          && style.visibility !== 'hidden'
          && style.opacity !== '0';
        const hasTooltipText = tooltipTextPattern.test(text);
        if (!visible && !hasTooltipText) return;
        if (!text && !html) return;
        out.push({
          selector,
          text,
          html,
          width: rect ? rect.width : 0,
          height: rect ? rect.height : 0,
          x: rect ? rect.x : 0,
          y: rect ? rect.y : 0
        });
      };
      selectors.forEach((selector) => {
        document.querySelectorAll(selector).forEach((node) => add(selector, node));
      });
      return out;
    }
    """


def patch_tooltip_reader(module):
    def read_tooltip_candidates(page):
        try:
            return page.evaluate(build_tooltip_reader_script())
        except Exception:
            return []

    module.read_tooltip_candidates = read_tooltip_candidates


def patch_tools_only_parser(module):
    original = getattr(module, "parse_tooltip_payload", None)
    if not callable(original):
        return

    def extract_revenue_tools_rank(tooltip_text):
        for line in str(tooltip_text or "").splitlines():
            low = line.lower()
            is_revenue = "revenue" in low or "grossing" in low or "收入排行" in line
            is_tools = "tools" in low or "utilities" in low or "工具" in line
            is_free = "top free" in low or "free" in low or "热门免费" in line
            if is_revenue and is_tools and not is_free:
                match = re.search(r"#\s*([0-9,]+)", line)
                if match:
                    return match.group(1).replace(",", "")
        return ""

    def parse_tooltip_payload_tools_only(tooltip_text):
        result = original(tooltip_text)
        if isinstance(result, dict):
            explicit_tools_rank = extract_revenue_tools_rank(tooltip_text)
            if explicit_tools_rank:
                result["revenue_rank_tools"] = explicit_tools_rank
            result["revenue_rank_apps"] = ""
            result["top_free_rank_tools"] = ""
        return result

    module.parse_tooltip_payload = parse_tooltip_payload_tools_only


def main():
    mod = load_snapshot_module()
    patch_tooltip_reader(mod)
    patch_tools_only_parser(mod)
    brands = [brand.lower() for brand in parse_csv_env("ST_PRODUCTS", list(PRODUCT_MAP))]
    countries = [country.upper() for country in parse_csv_env("ST_COUNTRIES", DEFAULT_COUNTRIES)]
    unknown = [brand for brand in brands if brand not in PRODUCT_MAP]
    if unknown:
        raise ValueError(f"Unknown products: {unknown}")

    mod.PRODUCTS = [{"brand": brand, "package": PRODUCT_MAP[brand]} for brand in brands]
    mod.COUNTRIES = countries
    mod.SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")
    mod.LOG_DIR = os.path.join(BASE_DIR, "logs")
    mod.OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    mod.TOOLTIP_HTML_DIR = os.path.join(mod.LOG_DIR, "tooltip_html")

    set_if_present(mod, "SAFE_MODE", False)
    set_if_present(mod, "DAILY_TASK_LIMIT", 9999)
    set_if_present(mod, "RESUME_MODE", False)
    set_if_present(mod, "MAX_RETRY", 0)
    set_if_present(mod, "PER_TASK_TIMEOUT_SECONDS", 45)
    set_if_present(mod, "TASK_GAP_MIN", 2)
    set_if_present(mod, "TASK_GAP_MAX", 4)
    set_if_present(mod, "BATCH_PAUSE_EVERY_MIN", 9999)
    set_if_present(mod, "BATCH_PAUSE_EVERY_MAX", 9999)
    set_if_present(mod, "BATCH_PAUSE_MIN", 1)
    set_if_present(mod, "BATCH_PAUSE_MAX", 1)
    set_if_present(mod, "RETRY_WAIT_MIN", 5)
    set_if_present(mod, "RETRY_WAIT_MAX", 8)
    return mod.main()


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(result if isinstance(result, int) else 0)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[SCRAPER_ERROR] {exc}")
        sys.exit(1)

