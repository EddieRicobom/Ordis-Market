# ORDIS MARKET — Research Report

> "Operator, I have investigated the available inventory systems. Good news: I found data. Bad news: I also found documentation from a slightly different decade." — Ordis

This research was conducted before any implementation code was written, per the
project brief. Sources are current as of August 2026.

---

## Inventory Source

**Finding: there is no official, sanctioned Warframe inventory export API.**
Every community tool works around this in one of three ways:

1. **Process memory scanning** — e.g. `gjrud/warframe-helper`, which explicitly
   "scans the running Warframe process's memory in fixed chunks" to obtain the
   session token needed to call Warframe's *mobile app* API. **This is exactly
   the technique this project is forbidden from using**, so it was ruled out
   immediately.
2. **AlecaFrame's `lastData.dat`** — a local cache file AlecaFrame (an
   Overwolf-based overlay) writes after it authenticates. Several tools
   (`browse.wf`, `WFHelper`) can *import* this file, but AlecaFrame itself is
   an Overwolf dependency, which this project explicitly avoids. We therefore
   do not depend on AlecaFrame or Overwolf, but we *do* support importing a
   plain JSON inventory file if an Operator already has one, exactly the way
   WFHelper's own "JSON import" option works.
3. **`warframe-api-helper` (Sainan)** — described as letting Operators
   "manually download your Warframe inventory," producing local
   `inventory.json` snapshots while logged into the game. It briefly reads
   Warframe's process memory to extract the current session's `accountId`
   and `nonce`, then uses those credentials to call Digital Extremes' own
   mobile-app API directly (the same one the official Android app uses;
   see also `cephalon-sofis/warframe_api`) — it does not inject code,
   modify the game, or automate anything, but the credential-extraction
   step does technically touch process memory, which is more than earlier
   drafts of this document credited it with. It is a separate, standalone
   tool the Operator runs themselves; Ordis Market does not bundle it,
   invoke it, or automate it in any way, and this correction is noted here
   deliberately rather than glossed over.

**Conclusion:** Ordis Market implements **manual file import only**. The
Operator obtains an inventory JSON file from a tool of their choosing (or
writes one by hand) and imports it through a file picker. Ordis Market never
touches the Warframe process, never authenticates to Digital Extremes, and
never automates any external helper tool.

## Inventory Format

There is no single standard shape. Observed formats include:

* A flat list of `{"name"/"ItemType": ..., "quantity"/"ItemCount": ...}`
  records.
* Nested, category-keyed arrays (`Suits`, `LongGuns`, `Pistols`, `Melee`,
  `MiscItems`, `Recipes`, ...), each an array of records keyed by an internal
  Warframe path such as `/Lotus/Powersuits/Mesa/MesaPrime` — this is the shape
  produced by the mobile-API-style tools referenced above.

`InventoryParser` (see `app/inventory/parser.py`) was written defensively to
accept both shapes (and Ordis Market's own normalized `{"items": [...]}`
shape), rather than betting on one specific tool's export format remaining
stable.

## Market API

**Base URL:** `https://api.warframe.market/v2` — the current, documented
API. Digital Extremes / warframe.market's own docs state plainly that "the
legacy v1 API is deprecated and unsupported. We do not plan to publish new v1
documentation," so this project targets v2 exclusively, even though the v2
contract is still pre-1.0 and evolving.

**Relevant endpoints used:**

* `GET /v2/orders/item/{slug}` — visible sell/buy orders for one item.
* `GET /v2/orders/recent` — most recent visible orders (not currently used,
  reserved for a future "trending" feature).
* An items index endpoint for catalog population (the exact v2 route for a
  full item collection was not fully documented at research time — the
  `/v2/versions` "manifests and collections" endpoint hints at a
  hash-versioned static collection rather than a simple `GET /v2/items`; the
  client code models this as `get_items()` and is isolated so it can be
  repointed if the exact collection route changes).

**Authentication:** None required or used. All endpoints Ordis Market calls
are public, read-only marketplace data. OAuth 2.0 for warframe.market is
explicitly still in development and "not available to public integrations
yet," so no auth flow was attempted or is needed for this project's scope.

**Rate limits:** warframe.market's published rules state a general limit of
**3 requests per second**, with stricter limits on some search-style
endpoints. `WarframeMarketClient` enforces this with a token-bucket limiter,
plus exponential backoff and `Retry-After` support on HTTP 429, and gives up
gracefully (raising `MarketRateLimitedError`) rather than hammering the API.

**Client etiquette:** warframe.market's rules require a descriptive
`User-Agent` identifying the application, and explicitly discourage
scraping/mirroring or disguising traffic as a browser. `WarframeMarketClient`
sends a fixed, honest `User-Agent: OrdisMarket/<version> (+repo url)` header.

## Item Database

Item metadata (name, category, Ducat value, tradability, set membership) is
sourced from warframe.market's own item index via `WarframeMarketClient`,
cached locally by `ItemCatalog`/`ItemCatalogUpdater` with a configurable TTL
(default 24h) so the full catalog is not re-downloaded on every launch.

## Safe Acquisition Method

**Manual file import**, exclusively. See "Inventory Source" above. No
automated acquisition is implemented.

## Known Limitations

* The exact v2 endpoint for a *complete* item collection was not fully
  confirmed against live documentation during research (the docs describe a
  hash-versioned "collections.items" manifest rather than a simple list
  endpoint). `ItemCatalogUpdater`/`get_items()` is isolated behind a single
  method so this can be adjusted without touching the rest of the app if the
  exact route differs at run time.
* Because there is no standard inventory export format, `InventoryParser`
  uses heuristics (checking several common field names) rather than a single
  fixed schema. Unusual or future export formats may require parser updates.
* Liquidity and price figures reflect only *currently visible* orders from
  online/in-game sellers, per warframe.market's own API behavior — this is
  an intentionally conservative, honest signal, not a guaranteed sale price.
