# ORDIS MARKET — Operator's Guide

> "Operator! You've arrived. I was starting to worry about the prices all by myself." — Ordis

This is the guide for people who just want to **use** Ordis Market,
without caring about the code. If you want to understand how the app
works under the hood, that's in `README.md` and `ARCHITECTURE.md` — this
guide is purely "how do I use this thing."

---

## What is this, exactly?

Ordis Market takes your Warframe inventory and compares it against real,
live prices on warframe.market, to tell you:

- how much your inventory is worth in Platinum;
- what's worth selling and what's worth keeping;
- whether it's better to sell a Prime part on its own or the whole set;
- whether it's better to sell for Platinum or hold onto it for Baro's
  Ducats.

It **never** touches the game itself — it never reads Warframe's memory,
never automates anything inside the game. It only reads a file you give
it and checks the market. It's a fancy calculator with a Cephalon's
personality attached.

---

## How to open the app

Two ways:

1. **Easiest**: double-click `run.bat`. It checks that you have Python
   installed, installs anything missing on its own, and opens the app.
2. From a terminal, if you prefer: `python run.py`

The very first time might take a moment while it installs dependencies.
After that, it opens quickly.

## How to update to a new version

Got a new copy of Ordis Market? Just replace all the files in this
folder with the new ones, then double-click `run.bat` again. That's the
entire process — there's no separate "build" or "compile" step to worry
about. Every time you open the app this way, it double-checks that all
its dependencies are installed and up to date on its own, so you never
need to run anything by hand.

If you'd like to double-check you're on the right version, look at the
title bar of the window (or the small subtitle right under "ORDIS
MARKET") — both show the current version number.

> You may notice a `build.bat` file in this folder too. Ignore it unless
> you specifically want a single standalone `.exe` that doesn't need
> Python installed at all — that path is more advanced and needs to be
> re-run after every update. For everyone else, `run.bat` is all you need.

---

## The full flow, step by step

### 1. You don't need to do anything before importing

The moment the app opens, it already fetches the item list from
warframe.market and the official item names (from Digital Extremes
itself) on its own. You don't need to click anything for that to happen.

### 2. Get your inventory in

Pick one of these three:

| Button | What it does |
|---|---|
| **GRAB INVENTORY** | Runs an external helper program you already have (like warframe-api-helper) and imports the result automatically. |
| **IMPORT INVENTORY** | You manually pick a `.json` file of your inventory. |
| **WATCH FOLDER** | Ordis Market keeps an eye on a folder and imports automatically whenever a new file shows up there. |

**LAUNCH WARFRAME** is just a shortcut to open the game through Steam —
it has nothing to do with importing your inventory, it's pure convenience.

> If you've already imported before, you don't need to do it again. The
> app remembers your last inventory and your last analysis, even after
> closing and reopening.

### 3. Click ANALYZE INVENTORY

This is the step that actually does the work: it cross-references your
inventory with market prices and fills in the table.

While it runs, you'll see a progress bar and Ordis commenting on the
process (he complains a little sometimes — that's normal).

### 4. Read the table

Here's what each column means:

| Column | What it is |
|---|---|
| **Item** | The item's name. Mods show their rank in parentheses, e.g. "Serration (Rank 10)". |
| **Qty** | How many you own. |
| **Price** | The current cheapest live listing on the market. |
| **Total** | Price × Qty — how much that whole stack is worth. |
| **Liquidity** | How easy this is to actually sell (VERY HIGH = sells fast, VERY LOW = might sit a while). |
| **Score** | A 0–100 rating combining value, liquidity, and quantity. Higher = better sell candidate. |
| **Recommendation** | SELL, CONSIDER, or KEEP — the plain-language summary of Score. |
| **Ducats** | For Prime items with a Ducat value, shows whether Platinum or Ducats is the better deal. |
| **Wiki** | Direct link to the item's official Warframe Wiki page. |
| **Sell** | Direct link to the item's warframe.market page, so you can post the listing yourself. |

Click any column header to sort by it, spreadsheet-style. Click again to
reverse the order.

### 5. Use the filters if the list is huge

- **Search**: type part of an item's name.
- **All Items / Tradable Only / Prime Only**: filter by category.
- **Min Score**: only show items scoring above X.
- **Hide Prime Sets**: hides fully-assembled sets (like "Mesa Prime Set"),
  if you only want to see individual component prices.

### 6. The extra buttons (optional, use when needed)

| Button | When to use it |
|---|---|
| **UPDATE ITEMS** | If you think the catalog is out of date (rarely needed — it already refreshes itself). |
| **UPDATE MARKET** | If you want fresher prices, skipping whatever's already cached. |
| **UPDATE WIKI** | Looks up Wiki links for the items in your current analysis. **Can take a while** on a large inventory — that's expected, it's a polite, one-item-at-a-time lookup on a third-party site. It's fast on future runs, since it remembers what it already looked up. |
| **EXPORT** | Saves the current table to CSV, JSON, or Excel. |

You'll notice some of these buttons turn **grey (disabled)** until they'd
actually do something — for example, EXPORT only turns on once you've
analyzed something. If a button looks greyed out, hover over it: it'll
tell you what to do first.

**Everything has a tooltip.** Every button, filter, and even the column
headers in the table explain themselves if you hover the mouse over them
for a moment — if you're ever unsure what something does, just hover and
wait.

---

## How to tell what's already loaded

Right under the title, there are two status rows:

- **Total Items / Tradable / Estimated Value / Last Import / Last
  Analysis** — the summary of your current analysis.
- **Catalog / Item Names / Wiki Links** — how many items, names, and
  Wiki links Ordis already knows about, without needing to click
  anything to find out.

If you reopen the app and these are already filled in, that means it
remembered everything on its own — no need to click anything again
unless you actually changed your inventory.

---

## Common questions

**"Only some items got a price, the rest show N/A."**
The catalog probably doesn't recognize that item yet, or it genuinely
isn't sellable on the market (e.g. an already-built Warframe — only its
loose parts are tradable). Try clicking UPDATE ITEMS. The message after
analyzing will also tell you if the recognized-item ratio looks low.

**"UPDATE WIKI is taking forever."**
Expected the first time, especially with a large inventory. It's a
polite, one-item-at-a-time lookup on a third-party site. Next time,
names it already resolved are skipped automatically — it only takes a
while again if your inventory changes a lot.

**"An item showed up in red."**
That means something went wrong with it (not found, not tradable, or the
market didn't respond). Hover over the item's name to see the exact
reason.

**"I closed and reopened the app, is everything gone?"**
It shouldn't be — your last analysis is restored automatically. If you
re-imported a different inventory in the meantime, then yes, the old
analysis is cleared on purpose (since it would describe a different
inventory than the one you have now, and showing it would be misleading).

**"Can I fully trust these prices?"**
These are the prices **currently listed** on warframe.market — not a
guarantee of a sale, just a reference point. A listed price isn't
always a price that sells fast; check the Liquidity column too.

---

## What Ordis Market never does

- Never reads Warframe's process memory.
- Never modifies game files.
- Never automates gameplay, trading, or any in-game action.
- Never posts a sale listing by itself — the Sell button only opens the
  page for you to post it yourself.
- Never needs your password or login for anything.

If you want the technical reasoning behind those decisions, it's all in
`RESEARCH.md`.

---

*Questions, suggestions, or bugs: just say so. Ordis is always
"listening", even without ears.*
