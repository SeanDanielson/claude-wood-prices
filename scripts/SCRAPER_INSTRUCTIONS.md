# Auto-scrape instructions for the scheduled task

This file is the playbook the scheduled refresh task follows. The Claude session
running on the schedule reads this, executes the steps via Chrome MCP, and then
runs `regenerate.py`.

## Vendors

### Tree Trunk Sawmill — `https://www.thetreetrunksawmillandwoodshop.com/shop`

Single shop page. Products are rendered as a Wix Pro Gallery; the relevant data
lives in DOM text nodes containing `$NN ... shipping/handling`. There are no
per-product detail pages — `productUrl` always points to the shop landing page.

Extraction approach (run in `javascript_tool`):

```javascript
(async () => {
  // Trigger lazy-load: scroll to bottom, then walk back through in 350px chunks
  let last = 0;
  for (let i = 0; i < 30; i++) {
    window.scrollTo(0, document.documentElement.scrollHeight);
    await new Promise(r => setTimeout(r, 500));
    const h = document.documentElement.scrollHeight;
    if (h === last && i > 4) break; last = h;
  }
  window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 400));
  for (let y = 0; y < document.documentElement.scrollHeight + 800; y += 350) {
    window.scrollTo(0, y); await new Promise(r => setTimeout(r, 200));
  }

  // Walk text nodes for prices and find their parent product card
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
  const items = []; let node;
  while (node = walker.nextNode()) {
    const txt = node.nodeValue || '';
    if (txt.length < 200 && /\$\d/.test(txt)) {
      let parent = node.parentElement;
      for (let i = 0; i < 14 && parent; i++) {
        const pt = (parent.textContent || '').replace(/\s+/g,' ').trim();
        if (pt.length > 60 && pt.length < 1500
            && /Slab|Board|Burl|Cookie|Piece|Charcuterie|Block/i.test(pt)
            && pt.includes('$')) {
          items.push(pt.substring(0, 400));
          break;
        }
        parent = parent.parentElement;
      }
    }
  }
  return [...new Set(items)];
})();
```

Then parse each card text into `{name, species, T, W, L, price, priceLabel,
notes}`. Heuristic: the first line before "Approximate dimensions" is the name;
species inferred from name (Walnut/Cherry/Oak/Ash/etc.). Dimensions parsed from
strings like `3"T × 22 3/4"L × 12 1/4"W`. Price = first `$NNN` (or `NNN$` —
yes, occasionally reversed).

### Bloom & Johnson — `https://www.bloomandjohnson.com/`

Has separate category pages. Active inventory:

| Category | URL | Notes |
|---|---|---|
| Slab Collection | `/live-edge` | Walnut slabs, dimensions usually missing while drying |
| Mantels | `/mantels` | Dimensions encoded in product name |
| Reclaimed | `/reclaimed` | Currently quote-only — skip |
| Hardwood Lumber | `/rough-sawn` | Currently quote-only — skip |
| Timber Collection | `/timber-collection` | Quote-only — skip |
| Shorts | `/shorts` | Currently "coming soon" — skip |

For each scrapable category, run:

```javascript
(async () => {
  // wait for content
  for (let i = 0; i < 15; i++) {
    if (document.body.innerText.length > 500) break;
    await new Promise(r => setTimeout(r, 600));
  }
  // scroll for lazy load
  let last = 0;
  for (let i = 0; i < 30; i++) {
    window.scrollTo(0, document.documentElement.scrollHeight);
    await new Promise(r => setTimeout(r, 500));
    const h = document.documentElement.scrollHeight;
    if (h === last && i > 4) break; last = h;
  }
  window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 400));
  for (let y = 0; y < document.documentElement.scrollHeight + 800; y += 350) {
    window.scrollTo(0, y); await new Promise(r => setTimeout(r, 200));
  }
  // collect product anchors
  const anchors = Array.from(document.querySelectorAll('a[href*="/product/"]'));
  const seen = new Map();
  for (const a of anchors) {
    if (seen.has(a.href)) continue;
    let parent = a;
    for (let i = 0; i < 12; i++) {
      parent = parent.parentElement; if (!parent) break;
      const t = (parent.textContent || '').replace(/\s+/g,' ').trim();
      if (t.length > 20 && t.length < 600) { seen.set(a.href, { href: a.href, text: t }); break; }
    }
  }
  return [...seen.values()];
})();
```

For mantels, names look like `Ash Mantel 3.5" x 7.75" x 71" #2004` — parse
dimensions directly from name.

For walnut slabs, names look like `Walnut Slab #W11025` with no dimensions.
Open each product page to check for dimension info in the description; most
items currently say "Drying — completion Fall 2027" with no dims, so set
`T/W/L = null`.

## Output

After scraping, build the merged products array, write
`data/products.json` with a fresh `_meta.lastUpdated` (today's ISO date),
then run `python3 scripts/regenerate.py`. Move any old input files from
`data/inputs/` to `data/processed/` if applicable.

## On vendor-block fallback

If a vendor's domain returns "Navigation to this domain is not allowed" or
"EGRESS_BLOCKED" (as B&J recently was), skip that vendor's refresh. Keep the
existing entries in `products.json` and tag a `_meta.warnings` array with the
block reason and timestamp. Tree Trunk should always succeed; B&J access has
been intermittent.
