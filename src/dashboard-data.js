import { BRAND_LABELS, COUNTRIES, COUNTRY_NAMES, PRODUCTS } from './config.js';

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
  const seriesRows = rows.map(normalizeRankingRow).sort(compareRows);
  const latestDate = latestDateFrom(seriesRows) || latestDateFrom(runs.map(normalizeRun)) || '';
  const latestByPair = new Map();

  for (const row of seriesRows) {
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
  const overview = {
    success_count: latestRows.filter((row) => row.status === 'SUCCESS').length,
    pending_count: latestRows.filter((row) => row.status === 'PENDING_TODAY').length,
    failed_count: latestRows.filter((row) => row.status !== 'SUCCESS' && row.status !== 'PENDING_TODAY').length,
    product_count: PRODUCTS.length,
    country_count: COUNTRIES.length,
    latest_monitor_date: latestDate,
    last_run_status: lastRun?.status || '',
  };

  return {
    generated_at: nowIso,
    latest_monitor_file_date: latestDate,
    overview,
    brands: PRODUCTS,
    brand_labels: BRAND_LABELS,
    countries: COUNTRIES,
    country_names: COUNTRY_NAMES,
    latest_rows: latestRows,
    series_rows: seriesRows,
  };
}

function normalizeRankingRow(row) {
  const revenueRankTools = normalizeRank(row.revenue_rank_tools);
  const normalized = {
    date: normalizeDate(row),
    brand: String(row.brand ?? row.product ?? '').toLowerCase(),
    country: String(row.country ?? '').toUpperCase(),
    status: normalizeStatus(row.status, revenueRankTools),
    data_origin: row.data_origin ?? row.source ?? 'unknown',
    revenue_rank_tools: revenueRankTools,
  };

  for (const field of DETAIL_FIELDS) {
    if (row[field] !== undefined && row[field] !== null) {
      normalized[field] = row[field];
    }
  }

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
  return String(item.date ?? item.monitor_file_date ?? item.monitor_date ?? '').slice(0, 10);
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

function pendingRow(date, brand, country) {
  return {
    date,
    brand,
    country,
    status: 'PENDING_TODAY',
    data_origin: 'pending',
    revenue_rank_tools: null,
  };
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
