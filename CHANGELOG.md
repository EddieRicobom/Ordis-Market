# Changelog

## 2.1.0

**New**
* Original app icon (`assets/ordis_market.ico`, embedded by `build.bat`; the
  running window draws the same emblem in code). Regenerate with
  `python tools/make_icon.py`.
* HOME tab (summary, Baro / Prime Resurgence timers) and RELICS tab (which Prime
  sets your relics can complete).
* Keyboard shortcuts: `Ctrl+1/2/3`, `Ctrl+O`, `Ctrl+R`, `F5`, `Ctrl+E`, `Ctrl+F`.
* Window size, position, filters and sort are remembered (`data/ui_state.json`).
* Prices refresh in the background on launch (without forcing a refetch).
* ETA on the progress bar.

**UI polish**
* Market tab: stat strip instead of the big header, wrapping toolbar with grouped
  buttons, primary actions highlighted, LAUNCH WARFRAME and the version moved to
  the status bar, row counter, debounced Min Score, resizable Item column.
* Table: right-aligned numbers with thousands separators, colour-coded
  recommendation and liquidity.
* Empty states on Market and Relics that say why nothing is shown and how to fix it.
* Themed checkboxes, spin boxes, scrollbars, splitters, focus rings.

**Fixes / performance**
* Cached mod prices keep their rank (they used to come back as N/A).
* Catalog and name-index downloads run in a worker thread; UPDATE MARKET no
  longer freezes the window.
* The cheapest tail of the inventory reuses prices fetched in the last 12 h.
* Every JSON store is written atomically.

**Housekeeping**
* `APP_VERSION` is now 2.1.0 and the User-Agent points at the real repository.
* Removed the unused `ui_enhanced.py` dialog; docs and comments brought up to date.
