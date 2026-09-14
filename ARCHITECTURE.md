# ORDIS MARKET — Architecture

```
Inventory Export / Local File
        |
        v
InventoryParser (app/inventory/parser.py)
        |
        v
InventorySnapshot (app/inventory/models.py)  --persisted by-->  InventoryRepository
        |
        v
PortfolioAnalyzer (app/analysis/portfolio.py)
        |
        +--> ItemCatalog (app/catalog/*)         [item_id -> name, ducats, tradable, set info]
        |         ^
        |         | matched, in priority order: gameRef, item_id/slug,
        |         | raw name, then NameIndex-resolved name (below)
        |
        +--> NameIndex (app/catalog/name_index.py)
        |         ^
        |         | populated by warframe_export.fetch_unique_name_index()
        |         | -- Digital Extremes' own Public Export data, maps a raw
        |         | internal ItemType path straight to its real display
        |         | name, independent of warframe.market
        |
        +--> MarketRepository (app/market/repository.py)
                   |
                   +--> PriceCache (app/cache/cache_store.py)   [TTL disk cache, offline fallback]
                   |
                   +--> WarframeMarketClient (app/market/client.py)
                              |
                              v
                        warframe.market v2 HTTP API (read-only)
        |
        v
PriceAnalyzer / LiquidityAnalyzer / SellScoreAnalyzer / DucatAnalyzer / SetAnalyzer
(app/market/pricing.py, liquidity.py, sell_score.py, ducats.py, sets.py)
        |
        v
PortfolioReport (per-item ItemAnalysis rows)
        |
        +--> ui/main_window.py (PySide6 dashboard: filters, sort, table)
        |
        +--> export/exporter.py (CSV / JSON / XLSX)
```

There is deliberately **no** path from "Warframe Process" into this diagram.
The only external I/O this application performs is:

1. reading a local file the Operator explicitly selects (inventory import),
2. HTTP GET requests to `api.warframe.market` (read-only, unauthenticated),
3. reading/writing its own local cache and settings files under `data/`.

## Module responsibilities

| Module | Responsibility | Network I/O? |
|---|---|---|
| `bootstrap` | Checks + auto-installs/upgrades runtime dependencies (version-aware, not just presence) | Yes (pip) |
| `inventory.parser` | Bytes on disk -> `InventoryItem` list | No |
| `inventory.repository` | Persist/reload the last import | No |
| `catalog.catalog` | Slug -> item metadata store | No |
| `catalog.updater` | Decides when to refresh the catalog and name index | Yes (via client / warframe_export) |
| `catalog.name_index` | uniqueName -> display name store (Digital Extremes data) | No |
| `catalog.warframe_export` | Fetches DE's official Public Export uniqueName/name pairs | Yes |
| `catalog.wiki_index` | item name -> Warframe Wiki URL store | No |
| `catalog.wiki_index_builder` | Independent Wiki link resolution, never called from analysis | Yes (via wiki_client) |
| `integrations.wiki_client` | MediaWiki API client for wiki.warframe.com | Yes |
| `common.rate_limiter` | Shared token-bucket limiter (market client + wiki client) | No |
| `market.client` | Raw HTTP client for warframe.market v2 | Yes |
| `market.repository` | Cache-first orchestration over the client | Yes (delegated) |
| `market.pricing` | Sell-order list -> price quote | No |
| `market.liquidity` | Order counts -> liquidity level | No |
| `market.sell_score` | Price + liquidity + qty -> 0-100 score | No |
| `market.ducats` | Plat vs. Ducat comparison | No |
| `market.sets` | Set vs. components comparison | No |
| `analysis.portfolio` | Orchestrates the above per inventory item | Yes (delegated) |
| `analysis.report_repository` | Persists/restores the last completed analysis for instant startup | No |
| `export.exporter` | Report -> CSV/JSON/XLSX file | No |
| `integrations.launcher` | Opens `steam://run/230410` via the OS | No (delegates to OS/Steam) |
| `integrations.inventory_helper` | Starts an Operator-selected external `.exe` as its own process | No (delegates to OS; the external program may do its own I/O) |
| `inventory.watcher` | Polls a chosen folder for a new/updated import file | No |
| `ui.main_window` | PySide6 dashboard | No (delegates to analyzer) |
| `ui.filters` | Pure filter/sort helper logic (PySide6-free, unit-testable) | No |
| `ui.theme` | Warframe-inspired dark QSS stylesheet | No |
| `ui.loading_indicator` | Rotating spinner + cycling status text for long operations | No |
| `ord_isms.messages` | All personality strings, isolated | No |

All the pure-calculation modules (`pricing`, `liquidity`, `sell_score`,
`ducats`, `sets`, `parser`) have zero network or UI dependencies, which is
what makes them fully unit-testable with Python's built-in `unittest` and no
live warframe.market connection (see `tests/`).
