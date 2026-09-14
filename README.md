# ORDIS MARKET

### Warframe Inventory & Market Analyzer

> "Operator! I have analyzed your inventory. The results are... concerning." — Ordis

Ordis Market is a read-only Windows desktop tool that imports a Warframe
inventory export, cross-references it against live warframe.market prices,
and tells you what's worth selling, what's worth keeping for Ducats, and
whether a Prime set is worth more assembled or in pieces.

> **Just want to use the app, not read about its architecture?** See
> [USER_GUIDE.md](USER_GUIDE.md) (English) or
> [GUIA_DO_USUARIO.md](GUIA_DO_USUARIO.md) (Portuguese) for a plain,
> non-technical walkthrough of every button and column.


---

## Purpose

* Value your entire inventory in Platinum.
* Identify which owned items are actually tradable.
* Rank items by value, liquidity, and a combined Sell Score (0-100).
* Compare selling Prime parts for Platinum vs. keeping them for Ducats.
* Compare selling a Prime set assembled vs. selling its components.
* Export everything to CSV, JSON, or XLSX.

## What this app does **not** do

Ordis Market is strictly **read-only** and does not:

* read Warframe's process memory,
* inject DLLs or hook the game process,
* use Overwolf or depend on AlecaFrame,
* modify any Warframe files,
* automate gameplay, trading, or macros of any kind.

See [RESEARCH.md](RESEARCH.md) for why, and what was ruled out.

## Inventory Acquisition

**This is manual file import — nothing else.**

Ordis Market cannot read your inventory directly from the game (Digital
Extremes does not provide an official API for this, and this project refuses
to use memory-reading workarounds). Instead:

1. Use a tool of your choice to produce an inventory JSON file. `warframe-api-helper`
   (Sainan) is the most straightforward option — download it from its GitHub
   releases, run it while Warframe is open and you're logged in, and it saves
   `inventory.json` next to itself. Note: that tool briefly reads Warframe's
   process memory to obtain your current session credentials before calling
   Digital Extremes' own API directly — it doesn't inject code or automate
   anything, but it's worth knowing before you run it. If you'd rather avoid
   that entirely, you can hand-write a JSON file instead (format below).
2. In Ordis Market, click **IMPORT INVENTORY** and select that file, or
   set up **WATCH FOLDER** (below) to have it happen automatically.

Ordis, on why the app itself doesn't do this automatically:

> "Operator, I could automate this. But doing so would require techniques I
> have decided are inadvisable. Please provide the inventory file manually."

### LAUNCH WARFRAME, GRAB INVENTORY, and WATCH FOLDER

Three convenience features close the gap without Ordis Market ever touching
the game process:

* **LAUNCH WARFRAME** opens Steam's own `steam://run/230410` handler — the
  same thing a desktop shortcut or Steam's "Play" button does. Ordis Market
  has no visibility into the game after that; it only asks Steam to start it.
* **GRAB INVENTORY** starts an external helper program you point it at —
  e.g. [`warframe-api-helper`](https://github.com/Sainan/warframe-api-helper) —
  as its own separate process, exactly like double-clicking it yourself.
  The first click asks you to locate the `.exe`; it's remembered after that
  (Shift+Click to pick a different one later). Ordis Market does not run
  inside that program, does not read memory itself, and does not know or
  care how the helper obtains your inventory — it only starts it and then
  watches its folder for the resulting `inventory.json`.
* **WATCH FOLDER** lets you point Ordis Market at any folder and auto-import
  the moment `inventory.json` there is new or updated. Clicking **GRAB
  INVENTORY** automatically starts watching that helper's own folder for
  you, so in practice: click **GRAB INVENTORY** once, let the helper finish,
  and Ordis Market imports the result on its own.

### Supported file shapes

Ordis Market's own normalized format:

```json
{ "items": [ { "item_id": "mesa_prime_systems", "quantity": 2 } ] }
```

A generic name/quantity list:

```json
[ { "name": "Mesa Prime Neuroptics", "quantity": 3 } ]
```

Nested category exports (as produced by mobile-API-style tools):

```json
{ "MiscItems": [ { "ItemType": "/Lotus/Types/Items/MiscItems/OrokinCell", "ItemCount": 40 } ] }
```

A sample file is included at `data/sample_inventory.json`.

## Installation

**Most people should use this path.** There are two ways to run Ordis
Market, and they behave very differently when it comes to updating —
read the note at the end before picking one.

### Recommended: run from source (always up to date, no build step)

```bash
python run.py
```

or on Windows, just double-click `run.bat`.

This checks for PySide6, requests, and openpyxl — including whether an
*already-installed* copy is new enough, not just whether it's present at
all — and installs or upgrades anything needed via `pip` automatically.
You never need to run `pip install` yourself, and you never need to
"build" anything.

Requires Python 3.11+. If a package fails to install automatically (no
internet, restricted environment, etc.), Ordis will tell you plainly and
suggest running `pip install -r requirements.txt` manually.

**How to update to a new version:** replace all the files in this folder
with the new version's files, then double-click `run.bat` again. That's
it — there is no separate build/compile step with this path, because
`run.bat` runs the actual source files directly every time, so it's
always running whatever code is currently in the folder. Dependencies
are re-checked (and upgraded if the new version needs a newer minimum)
on every launch automatically. You can confirm which version you're
running from the app's title bar or the subtitle under the header — both
show the current version number.

If you'd rather manage the environment yourself instead of letting
`run.py` do it:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

(`python -m app.main` also has its own fallback auto-install attempt if
PySide6 is missing, but `run.py`/`run.bat` is the recommended entry
point for everyone else.)

### Advanced/optional: a standalone .exe (no Python installed at all)

See **Build**, below. This path exists only for people who specifically
don't want Python installed on their machine. **Unlike the source path
above, this one does require a rebuild every time you get new code** —
the `.exe` is a frozen snapshot taken at build time, so replacing files
in the folder does nothing until `build.bat` is run again. If you're not
sure which path you want, use the recommended source path above instead.

## Startup & State

Ordis Market remembers where you left off, so you rarely need to click
through the whole pipeline again:

* **Your last completed analysis is restored automatically.** Reopening
  the app shows the same table you had before, with a "Last Analysis:
  <date> (restored)" label, instead of an empty table — no re-click of
  ANALYZE INVENTORY needed unless something actually changed.
* **Re-importing a new/changed inventory clears the old analysis**
  automatically, since showing stale numbers for a different inventory
  would be actively misleading, not just outdated.
* A second status row shows what's already loaded — catalog item count,
  known item names, known Wiki links — so you can tell at a glance
  whether UPDATE ITEMS/UPDATE WIKI would actually do anything new.
* Buttons that can't do anything useful yet are disabled with a tooltip
  explaining what to do first (e.g. EXPORT is disabled until you've
  analyzed something). No more clicking a button just to get an error
  telling you what you already needed to do.

All of this is separate from the various TTL-based network caches
(catalog, name index, wiki index, price cache) — those cache *inputs* so
network calls aren't repeated; this caches the *computed analysis
output* so the whole pipeline doesn't need re-running at all on a normal
restart.

## Usage

1. Launch Ordis Market. It automatically checks the item catalog and
   Digital Extremes name index in the background — no need to click
   anything first.
2. Get your inventory in: **GRAB INVENTORY** (runs an external helper and
   auto-imports its output), **IMPORT INVENTORY** (pick a `.json` file
   manually), or **WATCH FOLDER** (auto-import whenever a chosen folder's
   file updates). If you've already imported before, this is saved — you
   can skip straight to step 3.
3. Click **ANALYZE INVENTORY** to price everything against warframe.market.
4. Use the search box, tradable/Prime filters, minimum score, and **Hide
   Prime Sets** to narrow the results. Click any column header to sort,
   spreadsheet-style.
5. Optional: **UPDATE ITEMS** force-refreshes the catalog, **UPDATE
   MARKET** re-prices ignoring the cache, **UPDATE WIKI** resolves Wiki
   links for what's currently analyzed (works only after step 3, and can
   take a while the first time on a large inventory).
6. Click **EXPORT** to save a CSV, JSON, or XLSX report.

## Market API

Ordis Market talks to warframe.market's public v2 HTTP API
(`https://api.warframe.market/v2`), read-only, unauthenticated, respecting
the published 3 requests/second rate limit with retry/backoff on HTTP 429.
See [RESEARCH.md](RESEARCH.md) for full details and sources.

## Pricing

Everything is priced from warframe.market's **live order book** — the v2
API doesn't expose historical trade data (that only exists on the
deprecated, unsupported v1 API), so this app doesn't pretend otherwise.
The **Price** column shows the current lowest live-listed price by
default (configurable to average/median/a trimmed "recommended" strategy
in settings).

**Mods at different fusion ranks are priced and listed separately.** The
same mod owned at, say, rank 7 and rank 10 shows as two distinct rows
(e.g. "Serration (Rank 7)" / "Serration (Rank 10)"), each priced only
against orders listed at that exact rank — a rank-0 and a rank-10 copy of
the same mod are not the same product, and blending their prices together
would misrepresent both.

## Wiki Links & Selling

Every recognized item gets a **Wiki** link in the table pointing to its
official [Warframe Wiki](https://wiki.warframe.com) page, and a **Sell**
link to its `warframe.market` listing page — one click short of posting
an order yourself (Ordis Market doesn't post orders automatically, since
that would require logging into your warframe.market account, which is
out of scope for a read-only tool). Click **UPDATE WIKI** to resolve links
for whatever's in your current analysis; this runs independently and
never slows down price/ranking analysis — the Wiki is a completely
separate data source from warframe.market and Digital Extremes' Public
Export.

**Expect the first run to take a while on a large inventory.** The Wiki
is a polite, rate-limited, third-party lookup — a real Warframe vault can
have well over a thousand distinct item names, and each one needs its own
request. The progress bar reflects real progress while this runs. All
mod ranks of the same mod (e.g. "Serration" at rank 0 and rank 10) share
a single lookup rather than one each, and names already resolved (or
already confirmed to have no Wiki page) are skipped automatically on
every future run — so only the first run is slow; after that, it's
close to instant unless your inventory changed.

## Table

Click any column header to sort ascending/descending, spreadsheet-style.
Numeric columns (Qty, Price, Total, Score) sort numerically, not
alphabetically; Liquidity and Recommendation sort by their natural order
(e.g. SELL > CONSIDER > KEEP), not alphabetically either. Use **Hide Prime
Sets** in the filter row to drop fully-assembled "X Prime Set" rows if you
only want to compare individual component prices.

## Item Catalog

Populated from warframe.market's item index and cached locally
(`data/catalog.json`), refreshed automatically once the cache exceeds its
TTL (default 24 hours) or when you click **UPDATE ITEMS**.

Matching a real inventory export's internal item paths against that
catalog is the hard part -- Warframe's own internal names (e.g.
`/Lotus/Types/Recipes/WarframeRecipes/RhinoBlueprint`) don't resemble
warframe.market's slugs or display names at all. **UPDATE ITEMS** also
refreshes a second, independent data source for this: Digital Extremes'
own official [Public Export](https://wiki.warframe.com/w/Public_Export)
data, which maps those internal paths straight to their real in-game
names. Ordis Market tries, in order: warframe.market's own internal
reference field (when present), the item's slug, its raw name, and
finally this DE name translation — so a blueprint that fails the first
three still resolves via the fourth.

## Cache & Offline Mode

Market order data is cached to `data/cache/` with a configurable TTL
(default 30 minutes). If the market is unreachable, Ordis Market falls back
to the last cached prices and marks them as stale rather than failing
outright.

## Limitations

* No official inventory export exists; format support is best-effort and may
  need updates if community export tools change their JSON shape.
* Liquidity and pricing reflect only currently visible, online listings —
  not a guarantee of what you'll actually get for an item.
* The Ducat/Platinum comparison uses a configurable personal reference value,
  not a "correct" universal answer.

## Security Considerations

* No credentials of any kind are used, stored, or logged.
* No process interaction with Warframe.exe, and no memory reading of any
  kind — this was evaluated and deliberately rejected; see below.
* No network calls other than to `api.warframe.market`.
* All import is local file reading; no file is ever written back into your
  Warframe installation.
* **LAUNCH WARFRAME** only opens a `steam://` URI — the OS/Steam handles
  everything after that; Ordis Market has no further visibility or control.
* **GRAB INVENTORY** only starts an executable you explicitly selected, as
  its own independent OS process (`subprocess.Popen`) — the same as
  double-clicking it. Ordis Market never inspects, reads from, or waits on
  that process; it only remembers the path you gave it (in a small local
  text file, not the game's memory) so you don't have to browse for it
  every time.
* **WATCH FOLDER** only polls the modification time of one file in a folder
  you explicitly select; it never scans, indexes, or reads anything else on
  disk.

### Why Ordis Market doesn't grab your inventory automatically

It would be technically possible for Ordis Market to replicate what
`warframe-api-helper` does — read Warframe's process memory for a session
token and call Digital Extremes' API directly. That was considered and
rejected: extracting a live session credential from a running game's memory
carries real account risk regardless of who performs it, and doing it inside
a general "market analyzer" tool is a different risk decision than running a
small, standalone tool at your own discretion. Ordis Market instead offers
**LAUNCH WARFRAME** (via Steam), **GRAB INVENTORY** (starts an external
helper of your choice as its own process), and **WATCH FOLDER** (auto-import
once that helper writes a file) to close the gap without crossing that line.

## Build

```bat
build.bat
```

This installs dependencies and runs PyInstaller with `--onefile --windowed`,
producing `dist/OrdisMarket.exe`. No separate Python installation is required
to *run* the resulting executable — but **you do need to run `build.bat`
again after every update to the source**, since the `.exe` is a frozen
snapshot of whatever the code looked like at build time. If you're
updating Ordis Market regularly, the recommended `run.bat` source path
(see **Installation** above) avoids this entirely — replacing files and
double-clicking `run.bat` is always enough there, with no rebuild step.

**`OrdisMarket.exe` is fully self-contained.** You can copy just that one
file anywhere — no `data/` folder, no other project files needed
alongside it. On first launch it creates its own `data/` and `logs/`
folders right next to itself, and (important, and previously a real bug
here) everything it creates stays there and is picked up again on every
future launch — catalog, cached prices, your last-imported inventory,
and your last analysis all persist normally, exactly like the source
(`run.bat`) path. This works because `app/config/settings.py` detects
when it's running as a frozen executable and anchors its data folder
next to the real `.exe`, rather than the temporary folder PyInstaller
extracts a `--onefile` build into at runtime (which gets deleted on
exit — anchoring there would have silently reset everything on every
single launch).

**If that folder isn't writable** (e.g. you placed `OrdisMarket.exe` in
`Program Files` without admin rights), it automatically falls back to a
per-user location instead of crashing — `%LOCALAPPDATA%\OrdisMarket` on
Windows, or `~/.ordis-market` if that variable isn't set. A warning is
logged when this happens so it's not a silent surprise. Simplest fix if
you'd rather keep data next to the `.exe`: move it to a folder you have
write access to (Desktop, Documents, or its own dedicated folder).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "Operator, this does not appear to be an inventory file." | The JSON doesn't match any recognized shape — see **Supported file shapes** above. |
| "The market has refused to cooperate." | warframe.market is unreachable or rate-limiting; Ordis Market will retry and fall back to cache automatically. |
| Items showing "N/A" liquidity | No visible orders were returned for that item at query time. |
| Build fails in `build.bat` | Confirm Python 3.11+ is on PATH and `pip install -r requirements.txt` succeeds first. |
| `OrdisMarket.exe` fails to start with a Qt/platform plugin error | Rare, but some PyInstaller + PySide6 combinations miss a plugin. Try rebuilding with `python -m PyInstaller --collect-all PySide6 --name OrdisMarket --onefile --windowed app\main.py` instead of the plain `build.bat` command. |
| `OrdisMarket.exe` seems to "forget" everything between launches | This was a real bug (data was written into PyInstaller's temporary extraction folder instead of next to the `.exe`) and is fixed as of this version — make sure you've rebuilt with the current source if you still see this. |

## Sources

See [RESEARCH.md](RESEARCH.md) for the full list of references consulted
(warframe.market developer docs, community client libraries, and inventory
export tools) and what was ruled in/out and why.

## Tests

```bash
python -m unittest discover -s tests -v
```

59 tests, all mocked — no live network calls are made by the test suite.

---

*Ordis Market is an unofficial, fan-made tool. It is not affiliated with
Digital Extremes or warframe.market.*
