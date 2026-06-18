import json
from pathlib import Path


def render_dashboard_html(data: dict):
    payload = json.dumps(data, ensure_ascii=False)
    html2canvas_path = Path(__file__).with_name("html2canvas.min.js")
    html2canvas_js = html2canvas_path.read_text(encoding="utf-8") if html2canvas_path.exists() else ""
    html2canvas_js = html2canvas_js.replace("</script>", "<\\/script>")
    html = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>竞品排名监测看板</title>
  <style>
    :root{
      --bg:#F5F7FB;--card:#FFFFFF;--line:#E5ECF6;--ink:#172448;--text:#334155;--muted:#64748B;--soft:#EEF4FF;
      --primary:#2F6BFF;--primary-weak:#EAF1FF;--good:#16A34A;--bad:#E11D48;--warn:#D97706;--orange:#F97316;
      --shadow:0 10px 28px rgba(23,36,72,.07);
    }
    *{box-sizing:border-box}
    body{margin:0;background:var(--bg);font-family:"Microsoft YaHei","PingFang SC",Arial,sans-serif;color:var(--text)}
    .wrap{max-width:1680px;margin:0 auto;padding:24px}
    .head{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;margin-bottom:18px}
    .brand{display:flex;gap:16px;align-items:flex-start}
    .logo{width:56px;height:56px;border-radius:14px;background:linear-gradient(135deg,#2F6BFF,#5B5CF6);color:#fff;display:grid;place-items:center;font-weight:800;font-size:20px}
    h1{margin:0;color:var(--ink);font-size:44px;line-height:1.1}
    .meta{display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-size:13px;color:var(--muted)}
    .head-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end}
    .nav{display:flex;gap:6px;background:#fff;border:1px solid var(--line);border-radius:16px;padding:6px;box-shadow:var(--shadow)}
    .nav button{border:0;background:transparent;border-radius:12px;padding:13px 22px;font-size:18px;font-weight:700;color:#64748B;cursor:pointer}
    .nav button.active{background:#F8FBFF;color:var(--primary);box-shadow:inset 0 -3px 0 var(--primary)}
    .export-btn{border:1px solid #CFE0FF;background:#fff;color:var(--primary);border-radius:13px;width:46px;height:46px;padding:0;font-size:0;font-weight:900;cursor:pointer;box-shadow:var(--shadow);display:grid;place-items:center}
    .export-btn:hover{background:#F8FBFF;border-color:#98B8FF}
    .export-btn:disabled{cursor:wait;opacity:.65}
    .section-export{border:1px solid #DCE8FF;background:#fff;color:var(--primary);border-radius:999px;width:34px;height:34px;padding:0;font-size:0;font-weight:900;cursor:pointer;display:grid;place-items:center;white-space:nowrap}
    .section-export:hover{background:#F8FBFF;border-color:#98B8FF}
    .section-export:disabled{cursor:wait;opacity:.65}
    .download-icon{width:20px;height:20px;display:block;background:currentColor;-webkit-mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' fill='none' stroke='black' stroke-width='2.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 3v12'/%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3Cpath d='M5 21h14'/%3E%3C/svg%3E") center/contain no-repeat;mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' fill='none' stroke='black' stroke-width='2.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 3v12'/%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3Cpath d='M5 21h14'/%3E%3C/svg%3E") center/contain no-repeat}
    .page{display:none}.page.active{display:block}
    .grid-main{display:grid;grid-template-columns:1.45fr 1fr;gap:18px}
    .grid-bottom{display:grid;grid-template-columns:1fr;gap:18px;margin-top:18px}
    .card{background:#fff;border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow)}
    .card-inner{padding:20px 22px;background:#fff;border-radius:18px}
    .title-row{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;background:#fff}
    .title{font-size:22px;font-weight:800;color:var(--ink)}
    .sub{font-size:13px;color:var(--muted);margin-top:5px}
    .toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
    .select{border:1px solid var(--line);background:#fff;border-radius:12px;padding:8px 12px;color:#334155;min-height:38px}
    .matrix{margin-top:14px;border:1px solid var(--line);border-radius:14px;overflow:auto;background:#fff}
    table{width:100%;border-collapse:separate;border-spacing:0;background:#fff}
    th,td{border-right:1px solid var(--line);border-bottom:1px solid var(--line);padding:11px 10px;text-align:center;font-size:13px;white-space:nowrap;background:#fff}
    th:last-child,td:last-child{border-right:0} tr:last-child td{border-bottom:0}
    th{background:#F8FAFE;color:#334155;font-size:15px;font-weight:800}
    .market-cell{text-align:left;font-weight:800;color:#172448}
    .brand-hl{background:#EAF3FF!important}
    .top-cell{background:#FFF8E1!important;outline:1px solid #F6C453;outline-offset:-1px}
    .top-badge{display:inline-block;margin-left:6px;border-radius:999px;background:#F4B43C;color:#643B00;padding:2px 6px;font-size:11px;font-weight:900;vertical-align:middle}
    .rank{font-size:17px;font-weight:900;color:#0F172A}
    .rank-date{display:block;margin-top:4px;font-size:12px;color:var(--muted);font-weight:700}
    .delta{display:inline-block;margin-left:4px;font-size:13px;font-weight:900}
    .up{color:var(--good)}.down{color:var(--bad)}.no-delta{color:#94A3B8;margin-left:4px}.new{display:inline-block;margin-left:6px;color:var(--good);background:#EAFBF2;border-radius:999px;padding:2px 7px;font-size:12px;font-weight:800}.fail{color:#94A3B8;font-weight:800}
    .legend{display:flex;justify-content:flex-end;gap:12px;flex-wrap:wrap;padding-top:12px;font-size:13px;color:var(--muted)}
    .alert-list{margin-top:12px;display:grid;gap:9px}
    .alert-item{display:block;border:1px solid #EEF2F8;border-radius:12px;padding:12px;text-decoration:none;color:inherit}
    .alert-item:hover{border-color:#BFD2FF;background:#FBFDFF}
    .alert-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.alert-head{font-weight:900;color:#172448}.alert-rank{font-size:18px;font-weight:900;color:#0F172A;white-space:nowrap}.alert-note{font-size:13px;color:#64748B;margin-top:7px;line-height:1.45}
    .idx{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;background:#EEF2FF;color:#64748B;font-size:12px;font-weight:800}
    .pill{border-radius:999px;padding:5px 10px;font-size:12px;font-weight:800;background:#FFF3E0;color:#C77700}
    .pill.bad{background:#FEE2E2;color:#B91C1C}.pill.good{background:#EAFBF2;color:#15803D}
    .focus{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px}
    .focus-col{border-left:1px solid var(--line);padding:4px 14px}.focus-col:first-child{border-left:0}
    .focus-h{font-size:14px;font-weight:800}.focus-v{font-size:22px;font-weight:900;color:#0F172A;margin-top:8px}.focus-s{font-size:13px;color:var(--muted);margin-top:5px;line-height:1.45}
    .trend{height:250px;margin-top:12px;border:1px solid var(--line);border-radius:14px;padding:10px;background:#FBFDFF}
    .grid-bottom .trend{height:330px}
    .trend svg{width:100%;height:100%}
    .empty{height:100%;display:grid;place-items:center;color:#94A3B8;font-size:13px}
    .mini-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px}
    .mini{border:1px solid var(--line);border-radius:12px;padding:10px;background:#FBFDFF}
    .mini h4{margin:0 0 8px;font-size:14px;color:#172448}.mini .trend{height:112px;margin-top:0;border:0;padding:0;background:transparent}
    .series-legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;font-size:12px;color:#64748B}
    .bottom-info{margin-top:18px;background:#EEF4FF;border:1px solid #D8E4FF;border-radius:14px;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;gap:12px;color:#35508B;font-size:14px}
    .link{color:var(--primary);text-decoration:none;font-weight:800}
    .ops-grid{display:grid;grid-template-columns:repeat(5,minmax(140px,1fr));gap:12px}
    .ops{padding:14px;border:1px solid var(--line);border-radius:14px;background:#FAFCFF}.ops .k{font-size:13px;color:#64748B}.ops .v{font-size:28px;font-weight:900;color:#172448;margin-top:8px}
    .tbl-wrap{margin-top:12px;max-height:430px;overflow:auto;border:1px solid var(--line);border-radius:14px;background:#fff}
    .exporting-card,.exporting-card .card-inner,.exporting-card .title-row,.exporting-card .matrix,.exporting-card table,.exporting-card th,.exporting-card td{background-color:#fff}
    .exporting-card .brand-hl{background-color:#EAF3FF!important}
    .exporting-card .top-cell{background-color:#FFF8E1!important}
    .tbl-wrap th,.tbl-wrap td{text-align:left;font-size:12px;padding:9px 10px}.tbl-wrap th{position:sticky;top:0;background:#F8FAFE;z-index:1}
    @media(max-width:1180px){h1{font-size:34px}.grid-main,.grid-bottom{grid-template-columns:1fr}.focus,.mini-grid{grid-template-columns:1fr}.ops-grid{grid-template-columns:repeat(2,1fr)}}
  </style>
</head>
<body>
<div class="wrap">
  <header class="head">
    <div class="brand">
      <div class="logo">ST</div>
      <div>
        <h1>竞品排名监测看板</h1>
        <div class="meta">
          <span>最新监测日期：<b id="latestDate"></b></span>
          <span>生成时间：<b id="generatedAt"></b></span>
          <span>数据来源：<b id="fetchMode"></b></span>
        </div>
      </div>
    </div>
    <div class="head-actions">
      <button id="exportImage" class="export-btn" data-export-exclude data-export-target=".wrap" data-export-name="dashboard" title="保存当前页面为 PNG 图片" aria-label="保存当前页面为 PNG 图片"><span class="download-icon" aria-hidden="true"></span></button>
      <div class="nav">
        <button id="tabHome" class="active">首页</button>
        <button id="tabData">数据管理</button>
      </div>
    </div>
  </header>

  <main id="pageHome" class="page active">
    <div class="grid-main">
      <section class="card" id="marketRankCard">
        <div class="card-inner">
          <div class="title-row">
            <div>
              <div class="title">云手机排名对比表格</div>
              <div class="sub">默认展示重点市场，排名数值越小越好；下拉可切换全部国家或潜力国家。</div>
            </div>
            <div class="toolbar">
              <button class="section-export" data-export-exclude data-export-target="#marketRankCard" data-export-name="market_rank" title="保存该版块为图片" aria-label="保存该版块为图片"><span class="download-icon" aria-hidden="true"></span></button>
              <select id="marketGroup" class="select">
                <option value="focus" selected>重点市场</option>
                <option value="potential">潜力国家</option>
                <option value="all">全部国家</option>
              </select>
            </div>
          </div>
          <div class="matrix">
            <table>
              <thead><tr><th style="width:18%">市场</th><th class="brand-hl">UGphone</th><th>redfinger</th><th>ldcloud</th><th>vsphone</th></tr></thead>
              <tbody id="marketTableRows"></tbody>
            </table>
          </div>
          <div class="legend"><div id="marketCount"></div></div>
        </div>
      </section>

      <div class="right-col">
        <section class="card" id="alertsCard">
          <div class="card-inner">
            <div class="title-row">
              <div>
                <div class="title">竞品异常动作</div>
                <div class="sub">监测竞品新进榜、快速上升、以及排名超过 UGphone 的市场。</div>
              </div>
              <div class="toolbar">
                <button class="section-export" data-export-exclude data-export-target="#alertsCard" data-export-name="alerts" title="保存该版块为图片" aria-label="保存该版块为图片"><span class="download-icon" aria-hidden="true"></span></button>
                <a class="link" href="#" id="goDataTop">查看全部</a>
              </div>
            </div>
            <div class="alert-list" id="alertList"></div>
          </div>
        </section>
        <section class="card" id="ugFocusCard">
          <div class="card-inner">
            <div class="title-row">
              <div class="title">UGphone 今日战况</div>
              <button class="section-export" data-export-exclude data-export-target="#ugFocusCard" data-export-name="ug_battle" title="保存该版块为图片" aria-label="保存该版块为图片"><span class="download-icon" aria-hidden="true"></span></button>
            </div>
            <div class="focus" id="ugFocus"></div>
          </div>
        </section>
      </div>
    </div>

    <div class="grid-bottom">
      <section class="card" id="trendCard">
        <div class="card-inner">
          <div class="title-row">
            <div>
              <div class="title">重点市场趋势图</div>
              <div class="sub">仅使用已抓取的真实排名数据。</div>
            </div>
            <div class="toolbar">
              <button class="section-export" data-export-exclude data-export-target="#trendCard" data-export-name="trend" title="保存该版块为图片" aria-label="保存该版块为图片"><span class="download-icon" aria-hidden="true"></span></button>
              <span class="sub">市场</span>
              <select id="trendCountry" class="select"></select>
            </div>
          </div>
          <div class="trend" id="bigTrend"></div>
          <div class="series-legend" id="trendLegend"></div>
        </div>
      </section>
    </div>

    <div class="bottom-info">
      <div id="reviewInfo"></div>
      <a href="#" id="goData" class="link">前往数据管理</a>
    </div>
  </main>

  <main id="pageData" class="page">
    <section class="card" id="opsCard"><div class="card-inner"><div class="title-row"><div class="title">抓取任务状态</div><button class="section-export" data-export-exclude data-export-target="#opsCard" data-export-name="ops" title="保存该版块为图片" aria-label="保存该版块为图片"><span class="download-icon" aria-hidden="true"></span></button></div><div class="ops-grid" id="opsGrid"></div></div></section>
    <section class="card" id="reviewCard" style="margin-top:18px"><div class="card-inner"><div class="title-row"><div class="title">需人工复核数据</div><button class="section-export" data-export-exclude data-export-target="#reviewCard" data-export-name="review_table" title="保存该版块为图片" aria-label="保存该版块为图片"><span class="download-icon" aria-hidden="true"></span></button></div><div class="tbl-wrap"><table><thead><tr><th>产品</th><th>国家</th><th>收入排行-工具</th><th>Tooltip 日期</th><th>状态</th><th>异常原因</th><th>页面链接</th><th>截图</th></tr></thead><tbody id="reviewBody"></tbody></table></div></div></section>
    <section class="card" id="rawCard" style="margin-top:18px"><div class="card-inner"><div class="title-row"><div class="title">原始数据记录</div><button class="section-export" data-export-exclude data-export-target="#rawCard" data-export-name="raw_table" title="保存该版块为图片" aria-label="保存该版块为图片"><span class="download-icon" aria-hidden="true"></span></button></div><div class="tbl-wrap"><table><thead><tr><th>监测日</th><th>产品</th><th>市场</th><th>收入排行-工具</th><th>状态</th><th>数据来源</th><th>页面 URL</th></tr></thead><tbody id="rawBody"></tbody></table></div></div></section>
  </main>
</div>

<script>
__HTML2CANVAS__
</script>
<script>
const DATA = __PAYLOAD__;
const BRAND_ORDER = ["ugphone","redfinger","ldcloud","vsphone"];
const BRAND_LABEL = {ugphone:"UGphone", redfinger:"redfinger", ldcloud:"ldcloud", vsphone:"vsphone"};
const COLORS = {ugphone:"#F84747", redfinger:"#2563EB", ldcloud:"#F4B43C", vsphone:"#7C3AED"};
const PACKAGES = {ugphone:"com.tykeji.ugphone", redfinger:"com.redfinger.global", ldcloud:"com.ld.cph.gl", vsphone:"com.vsphone.overseas"};
const GROUPS = {
  focus:["TH","VN","PH","BR","TR","MY","ID","HK"],
  potential:["TW","KR","US","MX","SG","JP","PL","DE","GB","IN","IT","FR"],
  all: DATA.countries || []
};
const COUNTRY_NAMES = {
  TH:"泰国",BR:"巴西",PH:"菲律宾",US:"美国",VN:"越南",TR:"土耳其",MX:"墨西哥",HK:"香港",TW:"台湾",
  ID:"印度尼西亚",KR:"韩国",JP:"日本",DE:"德国",GB:"英国",PL:"波兰",FR:"法国",MY:"马来西亚",IT:"意大利",SG:"新加坡",IN:"印度"
};
function byId(id){ return document.getElementById(id); }
function toNum(v){
  if(v===null || v===undefined) return null;
  const s = String(v).trim();
  if(!s) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}
function countryName(c){ return `${COUNTRY_NAMES[c] || c} ${c}`; }
function sourceUrl(r){ return r.source_url || `https://app.sensortower.com/overview/${r.package||PACKAGES[r.brand]||""}?country=${r.country}&tab=category_rankings`; }
function evidenceHref(p){ if(!p) return ""; return p.startsWith("screenshots/") ? `../${p}` : p; }
function latestDate(){ return DATA.overview.latest_monitor_date || DATA.latest_monitor_file_date || ""; }
function dataCountries(){
  const seen = new Set();
  const add = c => { if(c) seen.add(c); };
  (DATA.countries || []).forEach(add);
  (DATA.series_rows || []).forEach(r=>add(r.country));
  latestRows().forEach(r=>add(r.country));
  return [...seen];
}
function orderedDataCountries(){
  const countries = dataCountries();
  const order = new Map();
  GROUPS.focus.forEach((c,i)=>order.set(c,i));
  GROUPS.potential.forEach((c,i)=>order.set(c,100+i));
  countries.forEach((c,i)=>{ if(!order.has(c)) order.set(c,200+i); });
  return countries.sort((a,b)=>(order.get(a)-order.get(b)) || a.localeCompare(b));
}
function rankOf(row){ return toNum(row && row.revenue_rank_tools); }
function hasRank(row){ return rankOf(row)!==null; }
function rankDateIso(value){
  const s = String(value || "").trim();
  if(!s) return "";
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if(iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
  const m = s.match(/^([A-Za-z]+)\s+(\d{1,2})(?:,\s*(\d{4}))?$/);
  if(!m) return "";
  const months = {jan:1,january:1,feb:2,february:2,mar:3,march:3,apr:4,april:4,may:5,jun:6,june:6,jul:7,july:7,aug:8,august:8,sep:9,sept:9,september:9,oct:10,october:10,nov:11,november:11,dec:12,december:12};
  const month = months[m[1].toLowerCase()];
  if(!month) return "";
  const latest = latestDate();
  let year = m[3] ? Number(m[3]) : Number((latest || "").slice(0,4));
  if(!year) year = new Date().getFullYear();
  const pad = n => String(n).padStart(2,"0");
  let result = `${year}-${pad(month)}-${pad(Number(m[2]))}`;
  if(!m[3] && latest && result > latest){
    result = `${year-1}-${pad(month)}-${pad(Number(m[2]))}`;
  }
  return result;
}
function needsManualReview(row){
  if(!row || rankOf(row)===null) return false;
  const latest = latestDate();
  const rankDate = rankDateIso(row.tooltip_date);
  return !latest || !rankDate || rankDate !== latest;
}
function rowDate(row){ return (row.date || row.latest_fetch_date || row.crawl_time || latestDate() || "").slice(0,10); }
function latestRows(){ return DATA.latest_rows || []; }
function rowFor(brand,country){ return latestRows().find(r=>r.brand===brand && r.country===country); }
function shortRankDate(value){
  const s = String(value || "").trim();
  if(!s) return "";
  const m = s.match(/^([A-Za-z]+\\s+\\d{1,2})(?:,\\s*\\d{4})?$/);
  if(m) return m[1];
  const iso = s.match(/^(\\d{4})-(\\d{2})-(\\d{2})/);
  if(iso) return `${iso[2]}/${iso[3]}`;
  return s.replace(/,\\s*\\d{4}\\b/, "");
}
function seriesRows(){
  const map = new Map();
  (DATA.series_rows || []).forEach(r=>{
    if(!r.brand || !r.country || rankOf(r)===null) return;
    map.set(`${rowDate(r)}|${r.brand}|${r.country}`, {date:rowDate(r),brand:r.brand,country:r.country,rank:rankOf(r)});
  });
  latestRows().forEach(r=>{
    if(!r.brand || !r.country || rankOf(r)===null) return;
    map.set(`${latestDate()}|${r.brand}|${r.country}`, {date:latestDate(),brand:r.brand,country:r.country,rank:rankOf(r)});
  });
  return [...map.values()].sort((a,b)=>a.date.localeCompare(b.date));
}
function datesFor(country=null, days=7){
  const dates = [...new Set(seriesRows().filter(r=>!country || r.country===country).map(r=>r.date))].sort();
  return dates.slice(-days);
}
function seriesFor(brand,country,dates){
  const rows = seriesRows().filter(r=>r.brand===brand && r.country===country);
  const byDate = new Map(rows.map(r=>[r.date,r.rank]));
  return dates.map(d=>byDate.has(d)?byDate.get(d):null);
}
function previousRank(brand,country){
  const dates = datesFor(country, 8).filter(d=>d < latestDate());
  for(let i=dates.length-1;i>=0;i--){
    const hit = seriesRows().find(r=>r.date===dates[i] && r.brand===brand && r.country===country);
    if(hit) return hit.rank;
  }
  return null;
}
function cellHtml(row, prev){
  const cur = rankOf(row);
  if(cur===null) return `<span class="fail">-</span>`;
  let marker = "";
  if(prev===null){ marker = `<span class="new">新进榜</span>`; }
  else {
    const delta = prev - cur;
    if(delta > 2){ marker = `<span class="delta up">↑${delta}</span>`; }
    else if(delta < -2){ marker = `<span class="delta down">↓${Math.abs(delta)}</span>`; }
  }
  const date = shortRankDate(row && row.tooltip_date);
  return `<span class="rank">#${cur}</span>${marker}${date?`<span class="rank-date">${date}</span>`:""}`;
}
function renderMarketTable(){
  const group = byId("marketGroup").value;
  const countries = (GROUPS[group] || GROUPS.focus).filter(c=>latestRows().some(r=>r.country===c));
  byId("marketTableRows").innerHTML = countries.map(country=>{
    const cells = BRAND_ORDER.map(brand=>{
      const cls = brand==="ugphone" ? " class='brand-hl'" : "";
      return `<td${cls}>${cellHtml(rowFor(brand,country), previousRank(brand,country))}</td>`;
    }).join("");
    return `<tr><td class="market-cell">${countryName(country)}</td>${cells}</tr>`;
  }).join("");
  const label = group==="focus" ? "重点市场" : group==="potential" ? "潜力国家" : "全部国家";
  byId("marketCount").textContent = `${label}：${countries.length} 个市场`;
  refreshTrendOptions();
}
function previousRankInfo(brand,country){
  const dates = datesFor(country, 12).filter(d=>d < latestDate());
  for(let i=dates.length-1;i>=0;i--){
    const hit = seriesRows().find(r=>r.date===dates[i] && r.brand===brand && r.country===country);
    if(hit) return hit;
  }
  return null;
}
function hasPriorMarketObservation(country){
  return datesFor(country, 12).some(d=>d < latestDate());
}
function hasPriorRankHistory(brand,country){
  return seriesRows().some(r=>r.brand===brand && r.country===country && r.date < latestDate());
}
function isConsecutivePrevious(country, prevDate){
  const dates = datesFor(country, 12).filter(d=>d <= latestDate());
  const idx = dates.indexOf(latestDate());
  return idx > 0 && dates[idx-1] === prevDate;
}
function cellHtml(row, prev, isTop){
  const cur = rankOf(row);
  if(cur===null) return `<span class="fail">-</span>`;
  let marker = "";
  if(prev===null) marker = "";
  else {
    const delta = prev - cur;
    if(delta > 0) marker = `<span class="delta up">↑${delta}</span>`;
    else if(delta < 0) marker = `<span class="delta down">↓${Math.abs(delta)}</span>`;
    else marker = "";
  }
  const date = shortRankDate(row && row.tooltip_date);
  return `<span class="rank">#${cur}</span>${isTop?`<span class="top-badge">TOP</span>`:""}${marker}${date?`<span class="rank-date">${date}</span>`:""}`;
}
function renderMarketTable(){
  const group = byId("marketGroup").value;
  const countries = (GROUPS[group] || GROUPS.focus).filter(c=>latestRows().some(r=>r.country===c));
  byId("marketTableRows").innerHTML = countries.map(country=>{
    const ranked = BRAND_ORDER.map(brand=>({brand,row:rowFor(brand,country),rank:rankOf(rowFor(brand,country))})).filter(x=>x.rank!==null);
    const bestRank = ranked.length ? Math.min(...ranked.map(x=>x.rank)) : null;
    const cells = BRAND_ORDER.map(brand=>{
      const row = rowFor(brand,country);
      const isTop = bestRank!==null && rankOf(row)===bestRank;
      const classes = [brand==="ugphone" ? "brand-hl" : "", isTop ? "top-cell" : ""].filter(Boolean).join(" ");
      return `<td${classes ? ` class="${classes}"` : ""}>${cellHtml(row, previousRank(brand,country), isTop)}</td>`;
    }).join("");
    return `<tr><td class="market-cell">${countryName(country)}</td>${cells}</tr>`;
  }).join("");
  const label = group==="focus" ? "重点市场" : group==="potential" ? "潜力国家" : "全部国家";
  byId("marketCount").textContent = `${label}：${countries.length} 个市场`;
  refreshTrendOptions();
}
function renderAlerts(){
  const itemMap = new Map();
  const competitorBrands = ["vsphone","ldcloud","redfinger"];
  const ensureItem = (row) => {
    const key = `${row.brand}|${row.country}`;
    if(!itemMap.has(key)) itemMap.set(key, {row, triggers:[], details:[], priority:0, score:0});
    return itemMap.get(key);
  };
  const addTrigger = (row, trigger) => {
    const item = ensureItem(row);
    item.triggers.push(trigger.type);
    item.details.push(trigger.detail);
    item.priority = Math.max(item.priority, trigger.priority);
    item.score = Math.max(item.score, Math.abs(trigger.delta || 0));
  };
  latestRows().forEach(row=>{
    const cur = rankOf(row), prev = previousRank(row.brand,row.country);
    if(!competitorBrands.includes(row.brand) || cur===null) return;
    const ugRank = rankOf(rowFor("ugphone", row.country));
    if(prev===null) {
      addTrigger(row, {
        type:"竞品新进榜",
        delta:null,
        priority: ugRank!==null && cur < ugRank ? 3 : 1,
        detail:`${BRAND_LABEL[row.brand]} 在 ${countryName(row.country)} 新进入工具榜`
      });
    }
    if(prev!==null){
      const delta = prev - cur;
      if(delta>=20) {
        addTrigger(row, {
          type:"竞品快速上升",
          delta,
          priority:2,
          detail:`较上一监测日上升 ${delta} 名`
        });
      }
    }
    if(ugRank!==null && cur < ugRank) {
      addTrigger(row, {
        type:"超过 UGphone",
        delta: ugRank - cur,
        priority:4,
        detail:`领先 UGphone ${ugRank - cur} 名`
      });
    }
  });
  const sorted = [...itemMap.values()].sort((a,b)=>
    (b.priority-a.priority) || (b.triggers.length-a.triggers.length) || (b.score-a.score) || rankOf(a.row)-rankOf(b.row)
  );
  byId("alertList").innerHTML = sorted.slice(0,6).map((it,i)=>{
    const r = it.row, cur = rankOf(r);
    const ugRank = rankOf(rowFor("ugphone", r.country));
    const ugText = ugRank!==null ? `UGphone #${ugRank}` : "UGphone 无排名";
    const pills = it.triggers.map(type=>`<span class="pill ${type==="竞品新进榜"?"good":"bad"}">${type}</span>`).join("");
    return `<a class="alert-item" href="${sourceUrl(r)}" target="_blank" title="打开 Sensor Tower 原始页面"><div class="idx">${i+1}</div><div><div><b>${BRAND_LABEL[r.brand]||r.brand}</b> <span class="sub">${countryName(r.country)}</span></div><div class="sub">${it.details.join("；")} · ${ugText}</div></div><div class="rank">#${cur}</div><div>${pills}</div></a>`;
  }).join("") || `<div class="empty" style="height:88px">近 7 个监测日暂无竞品威胁预警。</div>`;
}
function dayValue(d){
  if(!d) return null;
  const t = Date.parse(`${d}T00:00:00`);
  return Number.isNaN(t) ? null : t;
}
function ageDaysFromLatest(d){
  const a = dayValue(d), b = dayValue(latestDate());
  if(a===null || b===null) return 9999;
  return Math.floor((b-a)/86400000);
}
function withinLife(d, days){
  const age = ageDaysFromLatest(d);
  return age >= 0 && age <= days;
}
function rankAtDate(brand, country, date){
  const hit = seriesRows().find(r=>r.brand===brand && r.country===country && r.date===date);
  return hit ? hit.rank : null;
}
function overtakeEventDate(brand, country){
  const dates = datesFor(country, 45).filter(d=>d<=latestDate()).sort();
  let inRun = false;
  let start = null;
  dates.forEach(d=>{
    const comp = rankAtDate(brand, country, d);
    const ug = rankAtDate("ugphone", country, d);
    const over = comp!==null && ug!==null && comp < ug;
    if(over && !inRun){ start = d; inRun = true; }
    if(!over){ start = null; inRun = false; }
  });
  return start;
}
function renderAlerts(){
  const competitorBrands = ["redfinger","ldcloud","vsphone"];
  const ACTIONS = {
    overtake: {label:"\u8d85\u8fc7UG", priority:1, life:3},
    surge: {label:"\u6392\u540d\u66b4\u6da8", priority:2, life:7},
    reentry: {label:"\u91cd\u65b0\u8fdb\u699c", priority:3, life:7},
    newrank: {label:"\u65b0\u8fdb\u699c", priority:4, life:3},
    first: {label:"\u9996\u6b21\u76d1\u6d4b", priority:5, life:1}
  };
  const cards = [];
  const addAction = (item, key, eventDate, detail) => {
    const cfg = ACTIONS[key];
    if(!cfg || !withinLife(eventDate, cfg.life)) return;
    item.actions.push({...cfg, key, eventDate, detail});
  };
  latestRows().forEach(row=>{
    if(!competitorBrands.includes(row.brand)) return;
    const cur = rankOf(row);
    if(cur===null) return;
    const eventDate = rowDate(row) || latestDate();
    const ugRank = rankOf(rowFor("ugphone", row.country));
    const item = {row, cur, ugRank, actions:[], surgeDelta:0, prevRank:null, overGap: ugRank!==null ? ugRank-cur : 0};

    const overDate = overtakeEventDate(row.brand, row.country);
    if(ugRank!==null && cur < ugRank && overDate){
      addAction(item, "overtake", overDate, `\u9886\u5148UG ${ugRank-cur}\u540d`);
    }

    const prev = previousRankInfo(row.brand, row.country);
    if(prev){
      const delta = prev.rank - cur;
      const ratio = prev.rank > 0 ? delta / prev.rank : 0;
      item.prevRank = prev.rank;
      item.surgeDelta = delta;
      if(delta >= 30 || ratio >= 0.3){
        addAction(item, "surge", eventDate, `\u4ece#${prev.rank}\u5347\u81f3#${cur}\uff0c\u63d0\u5347${delta}\u540d`);
      }
      if(!isConsecutivePrevious(row.country, prev.date)){
        addAction(item, "reentry", eventDate, `\u6d88\u5931\u540e\u91cd\u65b0\u8fdb\u699c`);
      }
    } else if(hasPriorMarketObservation(row.country)){
      addAction(item, "newrank", eventDate, `\u6628\u65e5\u65e0\u6392\u540d \u2192 \u4eca\u65e5#${cur}`);
    } else {
      addAction(item, "first", eventDate, `\u9996\u6b21\u76d1\u6d4b\u5230#${cur}`);
    }

    if(item.actions.length){
      item.actions.sort((a,b)=>a.priority-b.priority);
      item.topPriority = item.actions[0].priority;
      item.hasCombo = item.actions.length > 1;
      cards.push(item);
    }
  });

  cards.sort((a,b)=>{
    if(a.hasCombo !== b.hasCombo) return a.hasCombo ? -1 : 1;
    if(a.topPriority !== b.topPriority) return a.topPriority - b.topPriority;
    if(a.overGap !== b.overGap) return b.overGap - a.overGap;
    if(a.surgeDelta !== b.surgeDelta) return b.surgeDelta - a.surgeDelta;
    return a.cur - b.cur;
  });

  const planFor = (item) => {
    const keys = item.actions.map(a=>a.key);
    if(keys.includes("overtake") && keys.includes("surge")) return "\u9700\u4f18\u5148\u590d\u6838\u539f\u6570\u636e\uff0c\u67e5\u770b\u6295\u653e\u548c\u5173\u952e\u8bcd\u53d8\u5316";
    if(keys.includes("overtake")) return "\u9700\u5173\u6ce8\u8be5\u5e02\u573a\u7ade\u54c1\u52a8\u4f5c";
    if(keys.includes("surge")) return "\u5efa\u8bae\u68c0\u67e5\u8be5\u5e02\u573a\u6d41\u91cf\u6765\u6e90\u53d8\u5316";
    if(keys.includes("reentry")) return "\u5efa\u8bae\u8ffd\u8e2a\u662f\u5426\u5f62\u6210\u8fde\u7eed\u6392\u540d";
    if(keys.includes("newrank")) return "\u5efa\u8bae\u7eb3\u5165\u540e\u7eed\u89c2\u5bdf";
    return "\u4f5c\u4e3a\u57fa\u7ebf\u8bb0\u5f55\uff0c\u6682\u4e0d\u4f5c\u5f3a\u63d0\u9192";
  };

  byId("alertList").innerHTML = cards.slice(0,6).map(item=>{
    const r = item.row;
    const sep = "\uff5c";
    const actionText = item.actions.map(a=>a.label).join("+");
    const pillClass = item.topPriority===1 ? "bad" : (item.topPriority<=3 ? "good" : "");
    const detailText = item.actions.map(a=>a.detail).filter(Boolean).join("\uff1b");
    const ugText = item.ugRank===null ? "UG\u6682\u65e0\u6392\u540d" : `UG#${item.ugRank}`;
    const note = `${detailText}\uff0c${ugText}\uff0c${planFor(item)}`;
    return `<a class="alert-item" href="${sourceUrl(r)}" target="_blank" title="\u6253\u5f00 Sensor Tower \u539f\u59cb\u9875\u9762"><div class="alert-top"><span class="alert-head">${BRAND_LABEL[r.brand]||r.brand}${sep}${countryName(r.country)}</span><span class="alert-rank">#${item.cur}</span><span class="pill ${pillClass}">${actionText}</span></div><div class="alert-note">${note}</div></a>`;
  }).join("") || `<div class="empty" style="height:88px">\u8fd1 7 \u4e2a\u76d1\u6d4b\u65e5\u6682\u65e0\u7ade\u54c1\u52a8\u4f5c\u9884\u8b66\u3002</div>`;
}
function renderUgFocus(){
  const focusCountries = GROUPS.focus;
  const ugRows = latestRows().filter(r=>r.brand==="ugphone" && focusCountries.includes(r.country) && rankOf(r)!==null);
  const wins = ugRows.filter(r=>{
    const ug = rankOf(r);
    return ["redfinger","ldcloud","vsphone"].every(b=>{
      const cr = rankOf(rowFor(b,r.country));
      return cr===null || ug < cr;
    });
  });
  const avg = ugRows.length ? Math.round(ugRows.reduce((sum,r)=>sum+rankOf(r),0)/ugRows.length) : null;
  const danger = [];
  GROUPS.focus.forEach(country=>{
    const ugRank = rankOf(rowFor("ugphone",country));
    if(ugRank===null) return;
    ["redfinger","ldcloud","vsphone"].forEach(b=>{
      const cr = rankOf(rowFor(b,country));
      if(cr!==null && cr < ugRank) danger.push({brand:b,country,rank:cr,gap:ugRank-cr});
    });
  });
  danger.sort((a,b)=>b.gap-a.gap || a.rank-b.rank);
  const winRate = ugRows.length ? Math.round((wins.length/ugRows.length)*100) : null;
  const dangerText = danger.length ? danger.slice(0,3).map(d=>`${BRAND_LABEL[d.brand]} ${countryName(d.country)} #${d.rank}`).join("；") : "暂无竞品领先";
  byId("ugFocus").innerHTML = [
    `<div class="focus-col"><div class="focus-h">核心市场胜率</div><div class="focus-v">${winRate===null?"-":winRate+"%"}</div><div class="focus-s">${wins.length}/${ugRows.length} 个每日重点市场排名领先竞品</div></div>`,
    `<div class="focus-col"><div class="focus-h" style="color:#F84747">平均排名</div><div class="focus-v">${avg===null?"-":"#"+avg}</div><div class="focus-s">基于 ${ugRows.length} 个每日重点市场的工具榜排名</div></div>`,
    `<div class="focus-col"><div class="focus-h" style="color:#E11D48">危险警告</div><div class="focus-v">${danger.length} 个</div><div class="focus-s">${dangerText}</div></div>`
  ].join("");
}
function drawTrend(containerId, country, brands=BRAND_ORDER, height=230){
  const el = byId(containerId);
  const dates = datesFor(country, 45);
  if(!dates.length){ el.innerHTML = `<div class="empty">暂无真实趋势数据</div>`; return; }
  const series = brands.map(brand=>({brand,values:seriesFor(brand,country,dates)})).filter(s=>s.values.some(v=>v!==null));
  if(!series.length){ el.innerHTML = `<div class="empty">暂无真实趋势数据</div>`; return; }
  const values = series.flatMap(s=>s.values).filter(v=>v!==null);
  const max = Math.max(20, ...values), min = Math.min(...values);
  const top = Math.max(1, min - 10), bottom = max + 20;
  const w = el.clientWidth || 650, h = height, m={l:42,r:56,t:14,b:30};
  const x = i => m.l + (i/(dates.length-1||1))*(w-m.l-m.r);
  const y = v => m.t + ((v-top)/(bottom-top))*(h-m.t-m.b);
  let svg = `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">`;
  [top, Math.round((top+bottom)/2), bottom].forEach(v=>{ const yy=y(v); svg+=`<line x1="${m.l}" y1="${yy}" x2="${w-m.r}" y2="${yy}" stroke="#E8EEF7"/><text x="${m.l-8}" y="${yy+4}" text-anchor="end" font-size="11" fill="#94A3B8">#${Math.round(v)}</text>`; });
  const labelEvery = Math.max(1, Math.ceil(dates.length / 10));
  dates.forEach((d,i)=>{
    if(i === 0 || i === dates.length - 1 || i % labelEvery === 0) {
      svg+=`<text x="${x(i)}" y="${h-8}" text-anchor="middle" font-size="11" fill="#94A3B8">${d.slice(5)}</text>`;
    }
  });
  series.forEach(s=>{
    const pts = s.values.map((v,i)=>v===null?null:`${x(i)},${y(v)}`).filter(Boolean).join(" ");
    svg += `<polyline points="${pts}" fill="none" stroke="${COLORS[s.brand]}" stroke-width="2.2"/>`;
    s.values.forEach((v,i)=>{ if(v!==null) svg += `<circle cx="${x(i)}" cy="${y(v)}" r="3" fill="${COLORS[s.brand]}"/>`; });
    const last = [...s.values].reverse().find(v=>v!==null);
    if(last!==undefined) svg += `<text x="${w-m.r+7}" y="${y(last)+4}" font-size="12" fill="${COLORS[s.brand]}" font-weight="800">#${last}</text>`;
  });
  svg += `</svg>`;
  el.innerHTML = svg;
}
function refreshTrendOptions(){
  const select = byId("trendCountry");
  const existing = select.value;
  const countries = orderedDataCountries();
  select.innerHTML = countries.map(c=>`<option value="${c}">${countryName(c)}</option>`).join("");
  select.value = countries.includes(existing) ? existing : (countries[0] || "");
  renderBigTrend();
}
function renderBigTrend(){
  const c = byId("trendCountry").value || orderedDataCountries()[0] || GROUPS.focus[0];
  drawTrend("bigTrend", c, BRAND_ORDER, 230);
}
function marketTier(country){
  if(GROUPS.focus.includes(country)) return "focus";
  if(GROUPS.potential.includes(country)) return "potential";
  return "all";
}
function marketTierLabel(country){
  const tier = marketTier(country);
  if(tier==="focus") return "每日";
  if(tier==="potential") return "每周";
  return "全部";
}
function renderLegends(){
  const html = BRAND_ORDER.map(b=>`<span style="color:${COLORS[b]};font-weight:800">${BRAND_LABEL[b]}</span>`).join("<span>·</span>");
  byId("trendLegend").innerHTML = html;
}
function renderOps(){
  const rows = latestRows();
  const cards = [
    ["今日任务", rows.length],
    ["成功", rows.filter(r=>r.status==="SUCCESS").length],
    ["部分成功", rows.filter(r=>r.status==="PARTIAL_SUCCESS").length],
    ["失败", rows.filter(r=>r.status==="RANK_CAPTURE_FAILED").length],
    ["复核项", DATA.overview.review_count || 0]
  ];
  byId("opsGrid").innerHTML = cards.map(c=>`<div class="ops"><div class="k">${c[0]}</div><div class="v">${c[1]}</div></div>`).join("");
  const reviewRows = rows.filter(needsManualReview).slice(0,160);
  byId("reviewBody").innerHTML = reviewRows.map(r=>`<tr><td>${BRAND_LABEL[r.brand]||r.brand}</td><td>${countryName(r.country)}</td><td>${r.revenue_rank_tools||"-"}</td><td>${r.tooltip_date||"-"}</td><td>${r.status||"-"}</td><td>排名日期非当日，需验证</td><td><a href="${sourceUrl(r)}" target="_blank">页面</a></td><td>${r.screenshot_path?`<a href="${evidenceHref(r.screenshot_path)}" target="_blank">截图</a>`:"-"}</td></tr>`).join("");
  byId("rawBody").innerHTML = rows.map(r=>`<tr><td>${r.latest_fetch_date||latestDate()}</td><td>${BRAND_LABEL[r.brand]||r.brand}</td><td>${countryName(r.country)}</td><td>${r.revenue_rank_tools||"-"}</td><td>${r.status||"-"}</td><td>${r.fetch_mode||"-"}</td><td><a href="${sourceUrl(r)}" target="_blank">URL</a></td></tr>`).join("");
}
function bindTabs(){
  const homeBtn=byId("tabHome"), dataBtn=byId("tabData"), home=byId("pageHome"), data=byId("pageData");
  function sw(toData){ home.classList.toggle("active",!toData); data.classList.toggle("active",toData); homeBtn.classList.toggle("active",!toData); dataBtn.classList.toggle("active",toData); }
  homeBtn.onclick=()=>sw(false); dataBtn.onclick=()=>sw(true); byId("goData").onclick=e=>{e.preventDefault();sw(true)}; byId("goDataTop").onclick=e=>{e.preventDefault();sw(true)};
}
async function exportDashboardImage(ev){
  const btn = ev && ev.currentTarget ? ev.currentTarget : byId("exportImage");
  if(!window.html2canvas){
    alert("图片导出组件加载失败，请刷新页面后重试。");
    return;
  }
  const targetSelector = btn.dataset.exportTarget || ".wrap";
  const target = document.querySelector(targetSelector);
  if(!target) return;
  const oldText = btn.innerHTML;
  const hiddenEls = Array.from(document.querySelectorAll("[data-export-exclude]"));
  btn.disabled = true;
  btn.innerHTML = "生成中...";
  hiddenEls.forEach(el=>el.style.visibility="hidden");
  target.classList.add("exporting-card");
  try{
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    const rect = target.getBoundingClientRect();
    const canvas = await html2canvas(target, {
      backgroundColor: "#FFFFFF",
      scale: Math.min(2, window.devicePixelRatio || 1.5),
      useCORS: true,
      logging: false,
      width: Math.ceil(rect.width),
      height: Math.ceil(rect.height),
      windowWidth: document.documentElement.clientWidth,
      windowHeight: document.documentElement.clientHeight
    });
    const link = document.createElement("a");
    const pageName = byId("pageData").classList.contains("active") ? "data" : "home";
    const exportName = btn.dataset.exportName || pageName;
    link.download = `competitor_dashboard_${latestDate() || "latest"}_${exportName}.png`;
    link.href = canvas.toDataURL("image/png");
    document.body.appendChild(link);
    link.click();
    link.remove();
  }catch(err){
    console.error(err);
    alert("图片生成失败，请刷新页面后重试。");
  }finally{
    target.classList.remove("exporting-card");
    hiddenEls.forEach(el=>el.style.visibility="");
    btn.disabled = false;
    btn.innerHTML = oldText;
  }
}
function boot(){
  byId("latestDate").textContent = latestDate() || "-";
  byId("generatedAt").textContent = DATA.generated_at || "-";
  byId("fetchMode").textContent = DATA.overview.fetch_mode || "全量监测";
  byId("marketGroup").onchange = renderMarketTable;
  byId("trendCountry").onchange = renderBigTrend;
  renderMarketTable();
  renderAlerts();
  renderUgFocus();
  renderLegends();
  renderOps();
  bindTabs();
  document.querySelectorAll("[data-export-target]").forEach(btn=>btn.onclick = exportDashboardImage);
  byId("reviewInfo").textContent = `当前 ${DATA.overview.review_count || 0} 条非当日排名需要复核，首页趋势图仅基于收入排行-工具绘制。`;
}
boot();
</script>
</body>
</html>"""
    return html.replace("__PAYLOAD__", payload).replace("__HTML2CANVAS__", html2canvas_js)








