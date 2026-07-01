import { APP_IDS, BRAND_LABELS, COUNTRIES, COUNTRY_NAMES, MARKET_TIERS, PRODUCTS } from './config.js';

const PRODUCT_ORDER = new Map(PRODUCTS.map((product, index) => [product, index]));
const COUNTRY_ORDER = new Map(COUNTRIES.map((country, index) => [country, index]));
const DETAIL_FIELDS = [
  'tooltip_date',
  'status_detail',
  'source_url',
  'crawl_time',
  'raw_tooltip_text',
  'screenshot_path',
];

export function buildDashboardPayload(rows = [], runs = [], nowIso = new Date().toISOString()) {
  const normalizedRows = rows.map(normalizeRankingRow).sort(compareRows);
  const latestDate = latestDateFrom(normalizedRows) || latestDateFrom(runs.map(normalizeRun)) || '';
  const latestByPair = new Map();

  for (const row of normalizedRows) {
    if (row.date === latestDate) {
      latestByPair.set(pairKey(row.brand, row.country), row);
    }
  }

  const latestRows = [];
  for (const brand of PRODUCTS) {
    for (const country of COUNTRIES) {
      const row = latestByPair.get(pairKey(brand, country));
      latestRows.push(row || pendingRow(latestDate, brand, country));
    }
  }

  const lastRun = latestRun(runs.map(normalizeRun));
  const todayCrawledCount = latestRows.filter((row) => row.data_origin !== 'pending').length;
  const partialCount = latestRows.filter((row) => row.status === 'PARTIAL_SUCCESS').length;
  const captureFailedCount = latestRows.filter((row) => isCaptureFailure(row.status)).length;
  const noCategoryDataCount = latestRows.filter((row) => isKnownNoDataStatus(row.status)).length;
  const reviewCount = latestRows.filter(needsManualReview).length;
  const overview = {
    success_count: latestRows.filter((row) => isSuccessfulStatus(row.status)).length,
    partial_count: partialCount,
    pending_count: latestRows.filter((row) => row.status === 'PENDING_TODAY').length,
    failed_count: latestRows.filter((row) => !isSuccessfulStatus(row.status) && !isKnownNoDataStatus(row.status) && row.status !== 'PENDING_TODAY').length,
    capture_failed_count: captureFailedCount,
    no_category_data_count: noCategoryDataCount,
    review_count: reviewCount,
    today_crawled_count: todayCrawledCount,
    today_uncrawled_count: latestRows.length - todayCrawledCount,
    history_fallback_count: latestRows.filter((row) => row.status === 'HISTORY_FALLBACK').length,
    rate_limited_count: latestRows.filter((row) => row.status === 'RATE_LIMITED').length,
    stale_history_count: latestRows.filter((row) => row.status === 'STALE_HISTORY').length,
    queue_remaining_count: latestRows.filter((row) => row.status === 'PENDING_TODAY').length,
    safe_limit_reached: false,
    product_count: PRODUCTS.length,
    country_count: COUNTRIES.length,
    latest_monitor_date: latestDate,
    last_run_status: lastRun?.status || '',
    fetch_mode: '每日自动监测',
    stale_after_days: 14,
  };

  return {
    generated_at: nowIso,
    latest_monitor_file_date: latestDate,
    overview,
    brands: PRODUCTS,
    brand_labels: BRAND_LABELS,
    countries: COUNTRIES,
    country_names: COUNTRY_NAMES,
    market_tiers: MARKET_TIERS,
    latest_rows: latestRows,
    series_rows: normalizedRows.map(slimSeriesRow),
  };
}

function slimSeriesRow(row) {
  return {
    date: row.date,
    brand: row.brand,
    country: row.country,
    status: row.status,
    revenue_rank_tools: row.revenue_rank_tools,
  };
}

function normalizeRankingRow(row) {
  const revenueRankTools = normalizeRank(row.revenue_rank_tools);
  const normalized = {
    date: normalizeDate(row),
    brand: String(row.brand ?? row.product ?? '').toLowerCase(),
    package: '',
    country: String(row.country ?? '').toUpperCase(),
    country_display: '',
    market_tier: '',
    status: normalizeStatus(row.status, revenueRankTools),
    data_origin: row.data_origin ?? row.source ?? 'unknown',
    revenue_rank_tools: revenueRankTools,
    revenue_rank_apps: null,
    top_free_rank_tools: null,
    latest_fetch_date: '',
    fetch_mode: '每日自动监测',
    data_quality_status: '',
    data_quality_detail: '',
    review_reason: '',
  };

  for (const field of DETAIL_FIELDS) {
    if (row[field] !== undefined && row[field] !== null) {
      normalized[field] = row[field];
    }
  }

  normalized.package = APP_IDS[normalized.brand] || '';
  normalized.country_display = countryDisplayName(normalized.country);
  normalized.market_tier = marketTierFor(normalized.country);
  normalized.latest_fetch_date = normalized.date;
  normalized.data_quality_detail = normalized.status_detail || '';
  const needsReview = needsManualReview(normalized);
  normalized.data_quality_status = needsReview ? 'need_review' : normalized.status === 'SUCCESS' || isKnownNoDataStatus(normalized.status) ? 'verified' : normalized.status === 'PENDING_TODAY' ? '' : 'need_review';
  normalized.review_reason = needsReview ? '排名日期非当日，需验证' : '';

  return normalized;
}

function normalizeRun(run) {
  return {
    date: normalizeDate(run),
    status: run.status ? String(run.status) : '',
    created_at: run.updated_at ? String(run.updated_at) : String(run.created_at ?? ''),
  };
}

function normalizeDate(item) {
  const date = String(item.date ?? item.monitor_file_date ?? item.monitor_date ?? '').trim();
  if (/^\d{8}$/.test(date)) {
    return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`;
  }
  return date.slice(0, 10);
}

function normalizeRank(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const rank = Number(value);
  return Number.isFinite(rank) ? rank : null;
}

function normalizeStatus(status, revenueRankTools) {
  if (status) {
    return String(status).toUpperCase();
  }
  return revenueRankTools === null ? 'FAILED' : 'SUCCESS';
}

function isSuccessfulStatus(status) {
  return status === 'SUCCESS' || status === 'PARTIAL_SUCCESS';
}

function isKnownNoDataStatus(status) {
  return status === 'NO_CATEGORY_RANKING_DATA';
}

function isCaptureFailure(status) {
  return ['FAILED', 'RANK_CAPTURE_FAILED', 'TOOLTIP_PARSE_FAILED', 'PAGE_LOAD_FAILED', 'CHART_NOT_FOUND', 'TOOLTIP_NOT_FOUND', 'RANK_TEXT_NOT_PARSED'].includes(status);
}

function needsManualReview(row) {
  if (row.revenue_rank_tools === null || row.revenue_rank_tools === undefined) {
    return false;
  }
  if (row.status === 'PARTIAL_SUCCESS' || isCaptureFailure(row.status) || row.status === 'RATE_LIMITED') {
    return true;
  }
  return Boolean(row.tooltip_date && row.date && normalizeTooltipDate(row.tooltip_date, row.date) !== row.date);
}

function normalizeTooltipDate(value, referenceDate) {
  const text = String(value || '').trim();
  if (!text) {
    return '';
  }
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) {
    return text.slice(0, 10);
  }

  const match = text.match(/^([A-Za-z]+)\s+(\d{1,2})(?:,\s*(\d{4}))?$/);
  if (!match) {
    return '';
  }

  const months = {
    jan: 1,
    january: 1,
    feb: 2,
    february: 2,
    mar: 3,
    march: 3,
    apr: 4,
    april: 4,
    may: 5,
    jun: 6,
    june: 6,
    jul: 7,
    july: 7,
    aug: 8,
    august: 8,
    sep: 9,
    sept: 9,
    september: 9,
    oct: 10,
    october: 10,
    nov: 11,
    november: 11,
    dec: 12,
    december: 12,
  };
  const month = months[match[1].toLowerCase()];
  if (!month) {
    return '';
  }

  const year = Number(match[3] || String(referenceDate).slice(0, 4));
  const day = Number(match[2]);
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function pendingRow(date, brand, country) {
  return {
    date,
    brand,
    package: APP_IDS[brand] || '',
    country,
    country_display: countryDisplayName(country),
    market_tier: marketTierFor(country),
    status: 'PENDING_TODAY',
    data_origin: 'pending',
    revenue_rank_tools: null,
    revenue_rank_apps: null,
    top_free_rank_tools: null,
    tooltip_date: '',
    latest_fetch_date: '',
    fetch_mode: '',
    data_quality_status: '',
    data_quality_detail: '今日尚未抓取',
    review_reason: '',
    source_url: sourceUrl(brand, country),
  };
}

function countryDisplayName(country) {
  const name = COUNTRY_NAMES[country] || '';
  return name ? `${name} ${country}` : country;
}

function marketTierFor(country) {
  for (const tier of Object.values(MARKET_TIERS)) {
    if (tier.countries.includes(country)) {
      return tier.label;
    }
  }
  return '';
}

function sourceUrl(brand, country) {
  const appId = APP_IDS[brand] || '';
  return appId && country ? `https://app.sensortower.com/overview/${appId}?country=${country}&tab=category_rankings` : '';
}

function latestDateFrom(items) {
  return items
    .map((item) => item.date)
    .filter(Boolean)
    .sort()
    .at(-1);
}

function latestRun(runs) {
  return runs
    .filter((run) => run.date || run.created_at)
    .sort((a, b) => {
      const dateCompare = a.date.localeCompare(b.date);
      return dateCompare || a.created_at.localeCompare(b.created_at);
    })
    .at(-1);
}

function compareRows(a, b) {
  const productCompare = orderOf(PRODUCT_ORDER, a.brand) - orderOf(PRODUCT_ORDER, b.brand);
  const countryCompare = orderOf(COUNTRY_ORDER, a.country) - orderOf(COUNTRY_ORDER, b.country);
  return a.date.localeCompare(b.date) || productCompare || countryCompare;
}

function orderOf(order, value) {
  return order.has(value) ? order.get(value) : Number.MAX_SAFE_INTEGER;
}

function pairKey(brand, country) {
  return `${brand}:${country}`;
}
