#!/usr/bin/env python3
"""Regenerate the wood-shop index.html from data/products.json.

Reads the products dataset (multi-vendor) and writes a self-contained
filterable HTML page. Run from the wood-shop/ folder root.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "products.json"
OUT = ROOT / "index.html"


def main() -> int:
    if not DATA.exists():
        print(f"products.json not found at {DATA}", file=sys.stderr)
        return 1
    payload = json.loads(DATA.read_text())
    meta = payload.get("_meta", {})
    products = payload.get("products", [])
    last_updated = meta.get("lastUpdated", dt.date.today().isoformat())
    vendors = meta.get("vendors", {})

    # JSON serialization for embedding into the page (we just dump the lot — the
    # page is small enough it's fine, and keeping vendor info on the client lets
    # us label cards / build the source filter without re-asking server-side).
    page_data = {
        "lastUpdated": last_updated,
        "vendors": vendors,
        "products": products,
    }

    body = TEMPLATE.replace("__DATA_JSON__", html.escape(json.dumps(page_data), quote=False))
    OUT.write_text(body)
    print(f"Wrote {OUT} — {len(products)} products from {len(vendors)} vendors")
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Wood Shop Curation</title>
<style>
  :root {
    --bg: #f6f1e7;
    --card: #ffffff;
    --ink: #2a1f14;
    --muted: #6b5945;
    --accent: #6e4a25;
    --accent-2: #8a5a2b;
    --tag-low: #2f7a3c;
    --tag-med: #b07418;
    --tag-high: #9a2a2a;
    --vendor-tt: #6e4a25;
    --vendor-bj: #2c5d6b;
    --shadow: 0 2px 8px rgba(60, 40, 20, 0.10);
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    font-family: Georgia, "Times New Roman", serif;
    background: var(--bg);
    color: var(--ink);
    line-height: 1.5;
  }
  header {
    background: linear-gradient(180deg, #3a2618 0%, #4a2f1c 100%);
    color: #f6f1e7;
    padding: 28px 24px;
    text-align: center;
  }
  header h1 { margin: 0 0 6px 0; font-size: 28px; letter-spacing: 1px; }
  header .sub { margin: 0; font-size: 14px; opacity: 0.85; }
  header a { color: #f6c98a; text-decoration: none; }
  header a:hover { text-decoration: underline; }
  main { max-width: 1200px; margin: 0 auto; padding: 24px; }

  .panel {
    background: var(--card);
    padding: 18px 20px;
    border-radius: 8px;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
  }
  .panel h2 { margin: 0 0 12px 0; font-size: 18px; color: var(--accent); }
  .panel .note { font-size: 12px; color: var(--muted); margin-top: 8px; font-style: italic; }

  .summary-wrap { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
  table.summary { width: 100%; border-collapse: collapse; font-size: 14px; min-width: 540px; }
  table.summary th, table.summary td {
    padding: 8px 10px; text-align: left; border-bottom: 1px solid #e6dcc6;
  }
  table.summary th {
    background: #efe4cc; color: var(--accent); font-weight: bold;
    text-transform: uppercase; font-size: 12px; letter-spacing: 0.6px;
  }
  table.summary td.num, table.summary th.num {
    text-align: right; font-family: "Courier New", monospace;
  }
  table.summary tr:hover td { background: #fbf6e8; }
  .vendor-pill {
    display: inline-block; font-size: 10px; text-transform: uppercase;
    letter-spacing: 0.6px; padding: 2px 6px; border-radius: 3px;
    color: #fff; vertical-align: middle; margin-left: 6px;
  }
  .vendor-pill.tree_trunk { background: var(--vendor-tt); }
  .vendor-pill.bloom_johnson { background: var(--vendor-bj); }

  .controls { display: flex; flex-wrap: wrap; gap: 10px 12px; align-items: center; }
  .controls .label { font-weight: bold; color: var(--accent); margin-right: 4px; }
  .filter-btn {
    border: 1.5px solid var(--accent);
    background: transparent; color: var(--accent);
    padding: 7px 14px; border-radius: 999px;
    cursor: pointer; font-family: inherit; font-size: 13px;
    transition: all 0.15s ease;
  }
  .filter-btn:hover { background: rgba(110, 74, 37, 0.08); }
  .filter-btn.active { background: var(--accent); color: #fff; }
  .filter-btn.active.bj { background: var(--vendor-bj); border-color: var(--vendor-bj); }
  .filter-btn.bj { border-color: var(--vendor-bj); color: var(--vendor-bj); }
  .filter-btn .range { font-size: 11px; opacity: 0.75; margin-left: 6px; }

  .search-input {
    flex: 1; min-width: 180px;
    padding: 8px 12px; border: 1.5px solid #c9b89a;
    border-radius: 6px; font-family: inherit; font-size: 14px;
    background: #fffefb;
  }
  .count { margin-left: auto; color: var(--muted); font-size: 13px; font-style: italic; }
  .mode-row { margin-top: 10px; font-size: 13px; }
  .mode-row label { margin-right: 14px; cursor: pointer; }
  .row-divider { width: 100%; height: 1px; background: #e6dcc6; margin: 6px 0; }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
    gap: 16px;
  }
  .card {
    background: var(--card);
    border-radius: 8px;
    padding: 16px 18px;
    box-shadow: var(--shadow);
    border-left: 5px solid var(--accent-2);
    display: flex; flex-direction: column; gap: 8px;
    position: relative;
  }
  .card.tree_trunk { border-left-color: var(--vendor-tt); }
  .card.bloom_johnson { border-left-color: var(--vendor-bj); }
  .card h3 { margin: 0; font-size: 17px; color: var(--accent); }
  .species { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.6px; }
  .dims { font-size: 13px; color: #4a3a28; font-family: "Courier New", monospace; }
  .bf { font-size: 12.5px; color: var(--muted); font-family: "Courier New", monospace; }
  .notes { font-size: 13px; color: #5b4a36; font-style: italic; }
  .footer-row {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: auto; padding-top: 8px; border-top: 1px dashed #d8c8ad;
  }
  .price-block { display: flex; flex-direction: column; }
  .price { font-size: 18px; font-weight: bold; color: var(--ink); }
  .price-bf { font-size: 12px; color: var(--accent-2); }
  .tier {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px;
    padding: 3px 8px; border-radius: 4px; color: #fff;
  }
  .tier-low  { background: var(--tag-low); }
  .tier-med  { background: var(--tag-med); }
  .tier-high { background: var(--tag-high); }
  .tier-na   { background: #888; }
  .view-link {
    display: inline-block; margin-top: 6px;
    font-size: 12.5px; color: var(--accent-2); text-decoration: none;
    border: 1px solid #d8c8ad; padding: 4px 10px; border-radius: 4px;
    align-self: flex-start;
  }
  .view-link:hover { background: #fbf6e8; }
  .view-link::after { content: " ↗"; }

  .empty {
    text-align: center; padding: 40px;
    color: var(--muted); font-style: italic;
  }
  footer {
    text-align: center; padding: 24px;
    font-size: 12px; color: var(--muted);
  }
  footer a { color: var(--accent-2); }

  /* ---------- Tablet (≤900px): tighter columns, smaller card min ---------- */
  @media (max-width: 900px) {
    main { padding: 16px; }
    .grid { grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
    .panel { padding: 14px 16px; }
  }

  /* ---------- Phone (≤640px): single-column, stacked filters, big touch targets ---------- */
  @media (max-width: 640px) {
    header { padding: 20px 16px; }
    header h1 { font-size: 22px; letter-spacing: 0.5px; }
    header .sub { font-size: 12px; line-height: 1.4; }
    main { padding: 12px; }

    .panel { padding: 12px 14px; margin-bottom: 14px; border-radius: 6px; }
    .panel h2 { font-size: 16px; margin-bottom: 10px; }
    .panel .note { font-size: 11px; }

    /* Summary table: scrolls horizontally inside .summary-wrap, shrink font */
    table.summary { font-size: 12px; }
    table.summary th, table.summary td { padding: 6px 8px; }
    table.summary th { font-size: 11px; letter-spacing: 0.4px; }

    /* Controls: stack vertically, full-width children, min 44px touch targets */
    .controls {
      gap: 8px;
      align-items: stretch;
    }
    .controls .label {
      width: 100%;
      margin-right: 0;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .filter-btn {
      flex: 1 1 calc(50% - 4px);
      min-height: 44px;
      padding: 10px 12px;
      font-size: 14px;
      text-align: center;
    }
    .filter-btn .range { display: none; }
    .search-input {
      flex: 1 1 100%;
      width: 100%;
      min-height: 44px;
      padding: 10px 12px;
      font-size: 16px; /* 16px prevents iOS zoom on focus */
    }
    .count {
      flex: 1 1 100%;
      margin-left: 0;
      text-align: center;
      font-size: 12px;
    }
    .mode-row {
      margin-top: 8px;
      font-size: 13px;
      line-height: 1.6;
    }
    .mode-row label { display: inline-block; margin-right: 12px; }
    #rangeHint { display: block; margin: 4px 0 0 0 !important; font-size: 11px; }

    /* Cards: 1 column, tighter padding */
    .grid { grid-template-columns: 1fr; gap: 10px; }
    .card { padding: 14px 14px; gap: 6px; border-left-width: 4px; }
    .card h3 { font-size: 16px; line-height: 1.3; }
    .species { font-size: 11px; }
    .dims, .bf { font-size: 12px; }
    .notes { font-size: 12px; }
    .price { font-size: 17px; }
    .price-bf { font-size: 11px; }
    .tier { font-size: 10px; padding: 3px 6px; }
    .view-link { font-size: 12px; padding: 8px 12px; min-height: 36px; }

    footer { padding: 16px 12px; font-size: 11px; }
  }

  /* ---------- Small phone (≤380px): one column filter buttons ---------- */
  @media (max-width: 380px) {
    .filter-btn { flex: 1 1 100%; }
  }
</style>
</head>
<body>

<header>
  <h1>Wood Shop Curation</h1>
  <p class="sub" id="headerSub">Loading…</p>
</header>

<main>

  <div class="panel">
    <h2>Average Price per Board Foot, by Wood Type</h2>
    <div class="summary-wrap">
    <table class="summary" id="summaryTable">
      <thead>
        <tr>
          <th>Wood Type</th>
          <th class="num">Items</th>
          <th class="num">Total BF</th>
          <th class="num">Total $</th>
          <th class="num">Avg $/BF</th>
          <th class="num">Min $/BF</th>
          <th class="num">Max $/BF</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
    </div>
    <p class="note">
      Board-foot (BF) = (Thickness × Width × Length, in inches) ÷ 144.
      Items missing a dimension or sold by the piece are excluded from BF averages.
      Aggregates apply the current Source filter.
    </p>
  </div>

  <div class="panel">
    <div class="controls">
      <span class="label">Source:</span>
      <button class="filter-btn active" data-source="all">All</button>
      <button class="filter-btn" data-source="tree_trunk">Tree Trunk</button>
      <button class="filter-btn bj" data-source="bloom_johnson">Bloom &amp; Johnson</button>
    </div>
    <div class="row-divider"></div>
    <div class="controls">
      <span class="label">Tier:</span>
      <button class="filter-btn active" data-tier="all">All</button>
      <button class="filter-btn" data-tier="low">Low</button>
      <button class="filter-btn" data-tier="med">Medium</button>
      <button class="filter-btn" data-tier="high">High</button>
      <input type="text" class="search-input" id="search" placeholder="Search by species, name, or notes…" />
      <span class="count" id="count"></span>
    </div>
    <div class="mode-row">
      <span class="label">Tier based on:</span>
      <label><input type="radio" name="mode" value="total" checked /> Total price</label>
      <label><input type="radio" name="mode" value="bf" /> Price per board-foot</label>
      <span id="rangeHint" style="color: var(--muted); margin-left: 8px;"></span>
    </div>
  </div>

  <div id="grid" class="grid"></div>
  <div id="empty" class="empty" style="display:none;">No items match your filters.</div>
</main>

<footer id="footer"></footer>

<script>
const PAGE_DATA = JSON.parse(document.currentScript.previousElementSibling ? "{}" : "{}");
</script>
<!-- data island -->
<script id="page-data" type="application/json">__DATA_JSON__</script>
<script>
(() => {
  const DATA = JSON.parse(document.getElementById('page-data').textContent);
  const VENDORS = DATA.vendors || {};
  const products = DATA.products || [];

  // Compute BF and $/BF on each item
  for (const p of products) {
    if (p.T != null && p.W != null && p.L != null) {
      p.bf = (p.T * p.W * p.L) / 144;
      p.dollarPerBF = p.price / p.bf;
    } else {
      p.bf = null; p.dollarPerBF = null;
    }
    const parts = [];
    if (p.T != null) parts.push(p.T + '"T');
    if (p.W != null) parts.push(p.W + '"W');
    if (p.L != null) parts.push(p.L + '"L');
    p.dims = parts.length ? parts.join(' × ') : '—';
  }

  // Header
  const subEl = document.getElementById('headerSub');
  const vendorBlurbs = Object.values(VENDORS).map(v =>
    `<a href="${v.shopUrl}" target="_blank" rel="noopener">${v.name}</a>`
  ).join(' &middot; ');
  subEl.innerHTML = `Curated from ${vendorBlurbs} &middot; data updated ${DATA.lastUpdated}`;

  // Footer
  const footerEl = document.getElementById('footer');
  footerEl.innerHTML = `
    <p>Inventory snapshot from ${DATA.lastUpdated}. Pricing may have changed since.</p>
    <p>${Object.values(VENDORS).map(v =>
      `Contact ${v.name}: <a href="${v.contactUrl}" target="_blank" rel="noopener">${v.contactUrl.replace(/^https?:\/\//,'')}</a>`
    ).join(' &middot; ')}</p>
  `;

  // Tier thresholds
  const TOTAL_TIERS = [
    { key: 'low', max: 100, label: 'Low (≤ $100)' },
    { key: 'med', max: 500, label: 'Medium ($101-$500)' },
    { key: 'high', max: Infinity, label: 'High (> $500)' }
  ];
  const BF_TIERS = [
    { key: 'low', max: 8, label: 'Low (≤ $8/BF)' },
    { key: 'med', max: 20, label: 'Medium ($8-$20/BF)' },
    { key: 'high', max: Infinity, label: 'High (> $20/BF)' }
  ];

  function tierFor(p, mode) {
    if (mode === 'bf') {
      if (p.dollarPerBF == null) return null;
      for (const t of BF_TIERS) if (p.dollarPerBF <= t.max) return t.key;
    } else {
      for (const t of TOTAL_TIERS) if (p.price <= t.max) return t.key;
    }
    return null;
  }
  function tierLabel(t) { return ({low:'Low', med:'Medium', high:'High'})[t] || 'n/a'; }

  // Summary
  function buildSummary(filtered) {
    const groups = new Map();
    for (const p of filtered) {
      if (!groups.has(p.species)) groups.set(p.species, { items:0, totalBF:0, totalPriced:0, perBF:[], vendors: new Set() });
      const g = groups.get(p.species);
      g.items++;
      g.vendors.add(p.vendor);
      if (p.bf != null) {
        g.totalBF += p.bf;
        g.totalPriced += p.price;
        g.perBF.push(p.dollarPerBF);
      }
    }
    const rows = [];
    for (const [species, g] of groups) {
      const avg = g.totalBF > 0 ? g.totalPriced / g.totalBF : null;
      const min = g.perBF.length ? Math.min(...g.perBF) : null;
      const max = g.perBF.length ? Math.max(...g.perBF) : null;
      rows.push({ species, items:g.items, totalBF:g.totalBF, totalPriced:g.totalPriced, avg, min, max, vendors: [...g.vendors] });
    }
    rows.sort((a, b) => {
      if (a.avg == null && b.avg == null) return a.species.localeCompare(b.species);
      if (a.avg == null) return 1;
      if (b.avg == null) return -1;
      return a.avg - b.avg;
    });
    const tbody = document.querySelector('#summaryTable tbody');
    tbody.innerHTML = '';
    for (const r of rows) {
      const tr = document.createElement('tr');
      const fmt = v => (v == null ? 'n/a' : '$' + v.toFixed(2));
      const fmtBF = v => (v === 0 || v == null ? 'n/a' : v.toFixed(2));
      const vendorPills = r.vendors.map(v => {
        const name = (VENDORS[v] && VENDORS[v].name) || v;
        const short = v === 'tree_trunk' ? 'TT' : v === 'bloom_johnson' ? 'B&J' : name;
        return `<span class="vendor-pill ${v}">${short}</span>`;
      }).join('');
      tr.innerHTML = `
        <td>${r.species} ${vendorPills}</td>
        <td class="num">${r.items}</td>
        <td class="num">${fmtBF(r.totalBF)}</td>
        <td class="num">$${(r.totalPriced || 0).toLocaleString()}</td>
        <td class="num"><strong>${fmt(r.avg)}</strong></td>
        <td class="num">${fmt(r.min)}</td>
        <td class="num">${fmt(r.max)}</td>
      `;
      tbody.appendChild(tr);
    }
  }

  // Render
  const grid = document.getElementById('grid');
  const empty = document.getElementById('empty');
  const countEl = document.getElementById('count');
  const searchInput = document.getElementById('search');
  const tierBtns = document.querySelectorAll('.filter-btn[data-tier]');
  const sourceBtns = document.querySelectorAll('.filter-btn[data-source]');
  const modeRadios = document.querySelectorAll('input[name="mode"]');
  const rangeHint = document.getElementById('rangeHint');

  let activeTier = 'all', activeSource = 'all', activeSearch = '', activeMode = 'total';

  function updateRangeHint() {
    const tiers = activeMode === 'bf' ? BF_TIERS : TOTAL_TIERS;
    rangeHint.textContent = '(' + tiers.map(t => t.label).join(' · ') + ')';
  }

  function render() {
    grid.innerHTML = '';
    const q = activeSearch.toLowerCase().trim();
    const filtered = [];
    for (const p of products) {
      if (activeSource !== 'all' && p.vendor !== activeSource) continue;
      const t = tierFor(p, activeMode);
      if (activeMode === 'bf' && t == null && activeTier !== 'all') continue;
      if (activeTier !== 'all' && t !== activeTier) continue;
      if (q) {
        const hay = (p.name + ' ' + p.species + ' ' + (p.notes || '')).toLowerCase();
        if (!hay.includes(q)) continue;
      }
      filtered.push(p);
    }
    buildSummary(filtered);
    let shown = 0;
    for (const p of filtered) {
      shown++;
      const t = tierFor(p, activeMode);
      const bfStr = p.bf != null ? `${p.bf.toFixed(2)} BF` : 'BF n/a (missing dim.)';
      const dpbfStr = p.dollarPerBF != null ? `$${p.dollarPerBF.toFixed(2)} / BF` : '—';
      const tierClass = t ? `tier-${t}` : 'tier-na';
      const tierTxt = t ? tierLabel(t) : 'n/a';
      const vendorName = (VENDORS[p.vendor] && VENDORS[p.vendor].name) || p.vendor;
      const linkLabel = p.vendor === 'bloom_johnson' ? 'View product' : 'View on shop';
      const card = document.createElement('div');
      card.className = `card ${p.vendor}`;
      card.innerHTML = `
        <div class="species">${p.species} <span class="vendor-pill ${p.vendor}">${p.vendor === 'tree_trunk' ? 'Tree Trunk' : 'B&J'}</span></div>
        <h3>${p.name}</h3>
        <div class="dims">${p.dims}</div>
        <div class="bf">${bfStr}</div>
        ${p.notes ? `<div class="notes">${p.notes}</div>` : ''}
        ${p.productUrl ? `<a class="view-link" href="${p.productUrl}" target="_blank" rel="noopener">${linkLabel}</a>` : ''}
        <div class="footer-row">
          <div class="price-block">
            <span class="price">${p.priceLabel}</span>
            <span class="price-bf">${dpbfStr}</span>
          </div>
          <span class="tier ${tierClass}">${tierTxt}</span>
        </div>
      `;
      grid.appendChild(card);
    }
    empty.style.display = shown === 0 ? 'block' : 'none';
    countEl.textContent = `${shown} of ${products.length} item${products.length === 1 ? '' : 's'}`;
  }

  tierBtns.forEach(b => b.addEventListener('click', () => {
    tierBtns.forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    activeTier = b.dataset.tier;
    render();
  }));
  sourceBtns.forEach(b => b.addEventListener('click', () => {
    sourceBtns.forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    activeSource = b.dataset.source;
    render();
  }));
  searchInput.addEventListener('input', e => { activeSearch = e.target.value; render(); });
  modeRadios.forEach(r => r.addEventListener('change', e => {
    activeMode = e.target.value; updateRangeHint(); render();
  }));

  updateRangeHint();
  render();
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main())
