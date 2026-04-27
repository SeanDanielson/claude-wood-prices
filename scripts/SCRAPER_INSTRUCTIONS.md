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

### Black Forest Sawmill — `https://blackforestsawmill.com`

Newly tracked. Site structure has not been characterized yet — the first
scheduled run that successfully reaches this domain should:

1. Open the root URL and inspect navigation for a shop / store / inventory
   page (common patterns: `/shop`, `/store`, `/inventory`, `/products`).
2. Confirm the contact / about path and update `_meta.vendors.black_forest`
   in `data/products.json` (`shopUrl`, `contactUrl`, `location`, `note`)
   with the real values.
3. Pick the closest extraction template from above:
   - If it's a Wix-style single-page gallery → reuse the Tree Trunk
     text-node walker.
   - If it has dedicated `/product/...` pages → reuse the Bloom & Johnson
     anchor collector.
4. Tag scraped items with `"vendor": "black_forest"`.

Until the structure is confirmed, treat this vendor like a blocked vendor:
keep zero entries in `products` and add a `_meta.warnings` note explaining
the pending characterization. The page will still render — the header
blurb iterates `_meta.vendors` generically, and the new filter button
simply shows zero results until real items land.

### Facebook Marketplace — Charlotte, NC only

Wired as the 4th source (`vendor: "fb_marketplace"`). **This tab is
scoped to the Charlotte, NC area only** — the city slug `charlotte` plus
a ~40-mile radius. Future runs MUST keep this scope; do not broaden it
without an explicit user request. The exact scope lives at
`_meta.vendors.fb_marketplace.scope` in `data/products.json` (`city`,
`state`, `locationSlug`, `radiusMiles`) — read from there rather than
hardcoding.

**Unauthenticated scraping is fully blocked** —
`https://www.facebook.com/marketplace/charlotte/`,
`/marketplace/charlotte/search?query=…`, and
`/marketplace/category/wood` all redirect to `/login` (HTTP 302), and
the rendered HTML contains no listing data. The 4th-source tab is wired
into the page; on each scheduled run, follow this sequence:

1. **Detect a session**: look for a Netscape-format cookie jar at the
   workspace root: `wood-shop/.fb-cookies` (gitignored, sibling of
   `.gh-token`). If absent, leave the `fb_marketplace` listings empty,
   ensure `_meta.warnings` still contains the `auth_required` entry, and
   skip the rest of this section. Do **not** fabricate listings.
2. **If the cookie jar exists**, load it via Chrome MCP (open a tab with
   `https://www.facebook.com/`, then for each cookie line in the jar
   inject it via `document.cookie = …` or, preferably, drive the browser
   while the user has Facebook signed in in their normal Chrome profile —
   the `Claude in Chrome` extension already runs in that profile).
3. **Search for relevant listings — Charlotte only**: read the scope
   block from `_meta.vendors.fb_marketplace.scope`. Visit
   `https://www.facebook.com/marketplace/{locationSlug}/search?query=<q>&radius={radiusMiles}`
   for each of these queries: `walnut slab`, `cherry slab`,
   `live edge slab`, `lumber`, `mantel`. For each, scroll to lazy-load
   (same scroll-then-walk pattern as Tree Trunk), then collect
   `a[href*="/marketplace/item/"]` anchors and walk each anchor's
   surrounding card text for title, price, location.
4. **Validate each listing's location** against the scope: parse the
   "City, ST" string from the card. Drop any listing whose city/state
   isn't Charlotte, NC or one of these adjacent ZIP-3-area towns within
   the 40-mile radius (Concord, Mooresville, Gastonia, Matthews,
   Huntersville, Cornelius, Indian Trail, Monroe, Pineville, Belmont,
   Mint Hill, Davidson, Harrisburg, Kannapolis, Salisbury, Statesville,
   Rock Hill SC, Fort Mill SC). When in doubt, drop. Better to ship 0
   listings than off-scope listings.
5. **Per-listing fields** (mirror the existing schema; leave T/W/L =
   null because peer-to-peer listings rarely give parseable dimensions):
   ```json
   {"vendor":"fb_marketplace","name":"<title>","species":"<inferred>",
    "T":null,"W":null,"L":null,"price":<number>,"priceLabel":"$<n>",
    "notes":"Location: <city, ST>. <free text snippet from listing>.",
    "productUrl":"https://www.facebook.com/marketplace/item/<id>"}
   ```
   Cap each query at the first ~25 listings to keep the page reasonable.
6. **Auth failure during run**: if Marketplace pages still redirect to
   `/login` despite the cookie jar (cookies expired, account suspended,
   etc.), don't write listings; refresh the `auth_required` warning's
   `since` date and `lastAttempt` timestamp instead.

The page renders an explicit empty-state message pulled from
`_meta.warnings[*]` whenever the active source filter has zero items in
the dataset, so the user always sees *why* the tab is empty rather than a
generic "no matches" string.

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
