# Wood Shop Curation

A live, filterable catalog of slabs, boards, mantels, and finished pieces from
two North Carolina mills:

- **The Tree Trunk Sawmill & Woodshop** (Westfield, NC) — small slabs, cookies, end-grain pieces, charcuterie boards.
- **Bloom & Johnson Millworks** (Davidson, NC) — premium live-edge walnut slabs and reclaimed mantels.

Each item is shown with dimensions, total price, and computed **price per board-foot**, with a per-wood-type summary table that updates as you filter.

## What's published

The hosted page is `index.html`. Open it directly in a browser, or — once the
repo is published to GitHub Pages — visit the public URL.

## Repo layout

```
.
├── index.html                  # Regenerated; never hand-edit
├── data/
│   ├── products.json           # Single source of truth (multi-vendor)
│   ├── inputs/                 # Optional drop-zone for manual exports
│   └── processed/              # Archive of consumed input files
└── scripts/
    ├── regenerate.py           # Reads products.json → writes index.html
    └── SCRAPER_INSTRUCTIONS.md # Playbook the auto-refresh task follows
```

## How updates happen

A scheduled Cowork task (`wood-shop-refresh`) runs **every Monday at 9 AM local time**:

1. Opens both vendors' product pages via Chrome MCP and scrapes the current inventory.
2. Replaces each vendor's entries in `data/products.json`, bumps `_meta.lastUpdated`.
3. Runs `python3 scripts/regenerate.py` to rebuild `index.html`.
4. Commits the changes and pushes to `origin main` so GitHub Pages republishes.

If a vendor's domain returns blocked (Bloom & Johnson access has been intermittent at the network-egress layer), the task keeps that vendor's existing entries and logs a warning under `_meta.warnings` — the page never goes blank because of an upstream block.

## Manual refresh

If you want to refresh without waiting for the schedule:

```bash
python3 scripts/regenerate.py    # rebuild index.html from products.json
```

Or run the scheduled task on demand from the Cowork **Scheduled** sidebar (`wood-shop-refresh` → Run now).

## License / data

Inventory data is read-only metadata (names, dimensions, prices, links) reproduced from each vendor's public shop page. All product imagery and IP belongs to the respective shops; click any "View product ↗" link to go to the actual listing.
