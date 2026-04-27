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
a ~40-mile radius (FB caps the radius slider at 25 mi in practice; that
is fine and tighter than the 40-mile target). Future runs MUST keep this
scope; do not broaden it without an explicit user request. The exact
scope lives at `_meta.vendors.fb_marketplace.scope` in
`data/products.json` (`city`, `state`, `locationSlug`, `radiusMiles`) —
read from there rather than hardcoding.

**Unauthenticated scraping is fully blocked** —
`/marketplace/charlotte/`, `/marketplace/charlotte/search?query=…`, and
`/marketplace/category/wood` all 302 to `/login`, and the rendered HTML
contains no listing data. We have two paths into authenticated data, in
preference order:

#### Primary: Claude-in-Chrome (use the user's logged-in profile)

1. **Pick a connected browser**: call
   `mcp__Claude_in_Chrome__list_connected_browsers` and select the
   user's local Chrome via `select_browser`. If no browser is
   connected, treat the source as blocked (see "Graceful no-op" below)
   — do **not** fall back to fabricated data.
2. **Open a tab and navigate** to
   `https://www.facebook.com/marketplace/{locationSlug}/search?query=<q>&radius={radiusMiles}`
   using the queries in step 4. The user is already signed in to
   Facebook in their normal Chrome profile, so the page renders real
   listings.
3. **Scroll-and-collect** with `javascript_tool`:
   - Scroll to bottom in chunks of `documentElement.scrollHeight` until
     the height stabilizes (FB lazy-loads).
   - Then walk back through in 400 px steps, collecting
     `a[href*="/marketplace/item/"]` anchors at each step. The DOM is
     virtualized — cards unmount once they're far above the viewport,
     so collect during the scroll, not after.
   - For each anchor, parse the structured `aria-label`, which has the
     reliable form `"<title>, $<price>, <city>, <state>, listing <id>"`.
     Build the canonical URL from the item id (NOT from `a.href`, which
     contains tracking query strings the extension censors).

   The exact extractor is checked into the schedule prompt; treat the
   block above as the spec.

#### Fallback: cookie jar (no live browser available)

If `mcp__Claude_in_Chrome__list_connected_browsers` returns an empty
list (e.g., the scheduled task fires at 9 AM Monday and the user's Mac
is asleep / Chrome isn't running), look for a Netscape-format cookie
jar at `wood-shop/.fb-cookies` (gitignored, sibling of `.gh-token`).
If present, drive a headless Chrome instance with those cookies and
reuse the same scroll-and-collect logic. If absent, see the next
section.

#### Graceful no-op

If neither a live Chrome session nor a cookie jar is available, do
**not** error and do **not** fabricate listings. Instead:

- Leave the existing `fb_marketplace` listings in `products.json`
  unchanged (so the page doesn't go blank between successful runs).
- Add a `_meta.warnings[]` entry like
  `{"vendor":"fb_marketplace","code":"no_session","message":"No
  Claude-in-Chrome browser connected and no cookie jar present;
  fb_marketplace listings left as-is from the prior run.","since":
  "<today>"}`.
- Continue the run for the other three vendors normally. FB never
  blocks the rest of the refresh.

#### Queries, caps, and quality bar (don't go crazy on volume)

Run **3–4 queries**, capped at **~25 listings each before dedupe**.
Recommended starter set: `wood`, `lumber`, `walnut slab`, `live edge`.
Add `mantel` or `hardwood` only if the others come back thin. The hard
target is **50–150 unique listings after dedupe + location filter**;
if you're trending past ~200, stop scraping and cut. Prefer quality
over breadth.

In each query, accept a listing only if:

- `price >= $5` (drops free-stuff and $1 placeholders).
- The title matches at least one keyword from
  `/(slab|lumber|live[ -]?edge|hard\s*wood|walnut|oak|cherry|maple|mantel|plank|beam|hickory|ash\b|cedar|poplar|sycamore|cypress|sassafras|pecan|kiln|bf\b|s2s|s4s|board)/i`.
- The aria-label parsed cleanly into `title, $price, city, ST,
  listing id` (drop sparse cards where one of those is missing).

#### Validate each listing's location

Parse the `City, ST` string from the aria-label. Drop anything whose
state isn't `NC` or `SC`, OR whose city isn't in the Charlotte allow-
list: Charlotte, Concord, Mooresville, Gastonia, Matthews, Huntersville,
Cornelius, Indian Trail, Monroe, Pineville, Belmont, Mint Hill,
Davidson, Harrisburg, Kannapolis, Salisbury, Statesville, Rock Hill,
Fort Mill, Tega Cay, Waxhaw, Stallings, Weddington, Marvin, Cramerton,
Mount Holly, Stanley, Lincolnton, Maiden, Denver, Lake Wylie, Catawba,
York, Clover. When in doubt, drop. Better to ship 0 than off-scope.

#### Per-listing schema (mirror the existing pattern)

```json
{"vendor":"fb_marketplace","name":"<title>","species":"<inferred>",
 "T":null,"W":null,"L":null,"price":<number>,"priceLabel":"$<n>",
 "notes":"Location: <city, ST>. Found via FB Marketplace search: \"<query>\". Peer-to-peer listing — no parseable dimensions.",
 "productUrl":"https://www.facebook.com/marketplace/item/<id>/"}
```

Leave `T/W/L = null` — peer-to-peer listings rarely give parseable
dimensions, and the page handles `null` by rendering "BF n/a".

#### Auth failure during run

If Marketplace pages still 302 to `/login` despite a connected browser
(account suspended, ratelimited, etc.), don't write listings; refresh
or add an `_meta.warnings[]` entry with `code: "auth_failed"` and a
`lastAttempt` timestamp.

The page renders an explicit empty-state message pulled from
`_meta.warnings[*]` whenever the active source filter has zero items in
the dataset, so the user always sees *why* the tab is empty rather than
a generic "no matches" string.

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
