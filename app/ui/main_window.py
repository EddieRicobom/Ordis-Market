"""
ui.main_window
===============

The Ordis Market dashboard.

Ordis: "Behold. A window. I have made it as informative as possible
        without becoming completely overwhelming. Mostly."
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.analysis.portfolio import ItemAnalysis, PortfolioAnalyzer, PortfolioReport
from app.analysis.report_repository import ReportRepository
from app.catalog.updater import ItemCatalogUpdater, NameIndexUpdater
from app.catalog.wiki_index_builder import WikiIndexBuilder
from app.config.settings import APP_VERSION
from app.export import exporter
from app.integrations.inventory_helper import (
    InventoryHelperLaunchError,
    launch_inventory_helper,
    load_saved_helper_path,
    save_helper_path,
)
from app.integrations.launcher import launch_warframe_via_steam
from app.inventory.parser import (
    InvalidInventoryFileError,
    InventoryFileNotFoundError,
    InventoryParser,
)
from app.inventory.repository import InventoryRepository
from app.inventory.watcher import InventoryFileWatcher
from app.market.ducats import DucatVerdict
from app.ord_isms import messages as ordis
from app.ui.loading_indicator import LoadingIndicator
from app.ui.filters import LIQUIDITY_SORT_RANK, RECOMMENDATION_SORT_RANK, is_prime_set_name
from app.ui.theme import ACCENT_CYAN, DANGER

logger = logging.getLogger("ordis_market.ui")


def _link_color() -> QColor:
    """A fresh QColor each call -- QTableWidgetItem takes ownership-ish
    semantics that make sharing one QColor instance across cells risky,
    so this is cheap and safe to call per-cell."""
    return QColor(ACCENT_CYAN)


class _SortableTableWidgetItem(QTableWidgetItem):
    """Displays formatted text (e.g. '83p') but sorts by an underlying
    numeric value, so clicking a column header sorts it like a real
    spreadsheet column instead of alphabetically (which would put '9p'
    after '84p')."""

    def __init__(self, text: str, sort_value: float) -> None:
        super().__init__(text)
        self._sort_value = sort_value

    def __lt__(self, other: object) -> bool:  # noqa: D105 - Qt override
        if isinstance(other, _SortableTableWidgetItem):
            return self._sort_value < other._sort_value
        return super().__lt__(other)


class _AnalysisWorker(QThread):
    """Runs PortfolioAnalyzer off the UI thread so the dashboard does not
    freeze while Ordis interrogates the merchants."""

    progress = Signal(int, int)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, analyzer: PortfolioAnalyzer, snapshot, force_refresh: bool = False):
        super().__init__()
        self._analyzer = analyzer
        self._snapshot = snapshot
        self._force_refresh = force_refresh

    def run(self) -> None:
        try:
            report = self._analyzer.analyze(
                self._snapshot,
                progress_callback=lambda i, n: self.progress.emit(i, n),
                force_refresh=self._force_refresh,
            )
            self.finished_ok.emit(report)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            logger.exception("Analysis failed")
            self.failed.emit(str(exc))


class _CatalogUpdateWorker(QThread):
    """Runs the catalog + name-index refresh off the UI thread, since both
    are network calls. The two are independent data sources (warframe.market
    vs. Digital Extremes' Public Export) but are refreshed together here
    since they're both triggered by the same UPDATE ITEMS button."""

    finished_ok = Signal(object, object)
    failed = Signal(str)

    def __init__(
        self,
        catalog_updater: ItemCatalogUpdater,
        force: bool,
        name_index_updater: Optional[NameIndexUpdater] = None,
    ):
        super().__init__()
        self._catalog_updater = catalog_updater
        self._name_index_updater = name_index_updater
        self._force = force

    def run(self) -> None:
        try:
            catalog_result = self._catalog_updater.ensure_fresh(force=self._force)
            name_index_result = None
            if self._name_index_updater is not None:
                name_index_result = self._name_index_updater.ensure_fresh(force=self._force)
            self.finished_ok.emit(catalog_result, name_index_result)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            logger.exception("Catalog update failed")
            self.failed.emit(str(exc))


class _WikiUpdateWorker(QThread):
    """Runs the Wiki link lookup off the UI thread.

    Deliberately separate from _CatalogUpdateWorker and _AnalysisWorker:
    the Wiki is a third, unrelated data source, and this must never share
    a thread (or run inline) with price/ranking analysis, so a slow or
    unavailable Wiki can never slow that down."""

    progress = Signal(int, int)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, builder: WikiIndexBuilder, names: list[str], force: bool = False):
        super().__init__()
        self._builder = builder
        self._names = names
        self._force = force

    def run(self) -> None:
        try:
            result = self._builder.build_for_names(
                self._names,
                force=self._force,
                progress_callback=lambda i, n: self.progress.emit(i, n),
            )
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            logger.exception("Wiki index update failed")
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(
        self,
        inventory_parser: InventoryParser,
        inventory_repository: InventoryRepository,
        portfolio_analyzer: PortfolioAnalyzer,
        catalog_updater: Optional[ItemCatalogUpdater] = None,
        name_index_updater: Optional[NameIndexUpdater] = None,
        wiki_index_builder: Optional[WikiIndexBuilder] = None,
        report_repository: Optional[ReportRepository] = None,
        initial_catalog_count: int = 0,
        initial_name_index_count: int = 0,
        initial_wiki_count: int = 0,
    ) -> None:
        super().__init__()
        self._parser = inventory_parser
        self._inventory_repo = inventory_repository
        self._analyzer = portfolio_analyzer
        self._catalog_updater = catalog_updater
        self._name_index_updater = name_index_updater
        self._wiki_index_builder = wiki_index_builder
        self._report_repo = report_repository
        self._initial_catalog_count = initial_catalog_count
        self._initial_name_index_count = initial_name_index_count
        self._initial_wiki_count = initial_wiki_count
        self._report: Optional[PortfolioReport] = None
        self._worker: Optional[_AnalysisWorker] = None
        self._catalog_worker: Optional[_CatalogUpdateWorker] = None
        self._wiki_worker: Optional[_WikiUpdateWorker] = None
        self._force_refresh_next_analysis = False
        self._watcher = InventoryFileWatcher()
        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(3000)  # poll every 3 seconds
        self._watch_timer.timeout.connect(self._on_watch_tick)

        self.setWindowTitle(f"ORDIS MARKET v{APP_VERSION}")
        self.resize(1180, 720)
        self._build_ui()
        self.lbl_catalog_status.setText(f"Catalog: {self._initial_catalog_count} items known")
        self.lbl_names_status.setText(f"Item Names: {self._initial_name_index_count} known")
        self.lbl_wiki_status.setText(f"Wiki Links: {self._initial_wiki_count} known")
        self._load_persisted_inventory()
        self._load_persisted_report()
        self._update_button_states()

    # -- UI construction -------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        header = QLabel("ORDIS MARKET")
        header.setObjectName("AppTitle")
        subtitle = QLabel(
            f"Inventory analysis and questionable financial decisions. — v{APP_VERSION}"
        )
        subtitle.setObjectName("AppSubtitle")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        summary_row = QHBoxLayout()
        self.lbl_total_items = QLabel("Total Items: -")
        self.lbl_total_items.setToolTip("How many distinct entries were found in your last imported inventory file.")
        self.lbl_tradable = QLabel("Tradable: -")
        self.lbl_tradable.setToolTip("How many of those items are actually sellable on warframe.market, per your last analysis.")
        self.lbl_value = QLabel("Estimated Value: -")
        self.lbl_value.setToolTip("Total Platinum value of every tradable item, added together, from your last analysis.")
        self.lbl_last_import = QLabel("Last Import: -")
        self.lbl_last_import.setToolTip("When your inventory file was last read in (via IMPORT INVENTORY, GRAB INVENTORY, or WATCH FOLDER).")
        self.lbl_last_analysis = QLabel("Last Analysis: -")
        self.lbl_last_analysis.setToolTip("When ANALYZE INVENTORY last ran. Shown as \"(restored)\" if this is left over from a previous session, not this one.")
        for lbl in (
            self.lbl_total_items,
            self.lbl_tradable,
            self.lbl_value,
            self.lbl_last_import,
            self.lbl_last_analysis,
        ):
            lbl.setObjectName("SummaryLabel")
            summary_row.addWidget(lbl)
        layout.addLayout(summary_row)

        # A second, quieter status row so the Operator can tell at a
        # glance what's already loaded (catalog/names/wiki) without
        # needing to click UPDATE ITEMS or UPDATE WIKI "just to check".
        status_row = QHBoxLayout()
        self.lbl_catalog_status = QLabel("Catalog: loading...")
        self.lbl_catalog_status.setToolTip("How many items warframe.market's catalog currently knows about. Refreshed by UPDATE ITEMS.")
        self.lbl_names_status = QLabel("Item Names: loading...")
        self.lbl_names_status.setToolTip("How many item display names are known from Digital Extremes' own Public Export data. Refreshed by UPDATE ITEMS.")
        self.lbl_wiki_status = QLabel("Wiki Links: 0 known")
        self.lbl_wiki_status.setToolTip("How many item names already have a resolved Warframe Wiki link cached. Refreshed by UPDATE WIKI.")
        for lbl in (self.lbl_catalog_status, self.lbl_names_status, self.lbl_wiki_status):
            lbl.setObjectName("SummaryLabel")
            status_row.addWidget(lbl)
        layout.addLayout(status_row)

        button_row = QHBoxLayout()
        self.btn_launch_warframe = QPushButton("LAUNCH WARFRAME")
        self.btn_launch_warframe.setToolTip(
            "Opens Warframe through Steam, the same as clicking Play in your library. "
            "Purely a convenience shortcut -- unrelated to importing your inventory."
        )
        self.btn_grab_inventory = QPushButton("GRAB INVENTORY")
        self.btn_grab_inventory.setToolTip(
            "Runs your warframe-api-helper.exe (or similar) as its own program "
            "and auto-imports the inventory.json it writes.\n"
            "First click asks you to locate it; Shift+Click to pick a different one later."
        )
        self.btn_import = QPushButton("IMPORT INVENTORY")
        self.btn_import.setToolTip(
            "Manually pick an inventory .json file from disk to import."
        )
        self.btn_watch_folder = QPushButton("WATCH FOLDER")
        self.btn_watch_folder.setToolTip(
            "Pick a folder to watch continuously; any time a new/updated inventory "
            "file appears there, it's imported automatically. Click again to stop watching."
        )
        self.btn_analyze = QPushButton("ANALYZE INVENTORY")
        self.btn_update_market = QPushButton("UPDATE MARKET")
        self.btn_update_items = QPushButton("UPDATE ITEMS")
        self.btn_update_items.setToolTip(
            "Force-refreshes the warframe.market item catalog and the Digital Extremes "
            "item name index. Rarely needed -- both already refresh automatically."
        )
        self.btn_update_wiki = QPushButton("UPDATE WIKI")
        self.btn_update_wiki.setToolTip(
            "Looks up official Warframe Wiki links for items in your current "
            "inventory/report. Runs independently of price analysis and never "
            "slows it down."
        )
        self.btn_export = QPushButton("EXPORT")
        for btn in (
            self.btn_launch_warframe,
            self.btn_grab_inventory,
            self.btn_import,
            self.btn_watch_folder,
            self.btn_analyze,
            self.btn_update_market,
            self.btn_update_items,
            self.btn_update_wiki,
            self.btn_export,
        ):
            button_row.addWidget(btn)
        layout.addLayout(button_row)

        self.btn_launch_warframe.clicked.connect(self._on_launch_warframe_clicked)
        self.btn_grab_inventory.clicked.connect(self._on_grab_inventory_clicked)
        self.btn_import.clicked.connect(self._on_import_clicked)
        self.btn_watch_folder.clicked.connect(self._on_watch_folder_clicked)
        self.btn_analyze.clicked.connect(self._on_analyze_clicked)
        self.btn_update_market.clicked.connect(self._on_update_market_clicked)
        self.btn_update_items.clicked.connect(self._on_update_items_clicked)
        self.btn_update_wiki.clicked.connect(self._on_update_wiki_clicked)
        self.btn_export.clicked.connect(self._on_export_clicked)

        filter_row = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search item name...")
        self.txt_search.setToolTip("Filters the table to items whose name contains this text (not case-sensitive).")
        self.chk_tradable_only = QComboBox()
        self.chk_tradable_only.addItems(["All Items", "Tradable Only", "Prime Only"])
        self.chk_tradable_only.setToolTip(
            "All Items: no filtering.\n"
            "Tradable Only: hide items that can't actually be sold on warframe.market.\n"
            "Prime Only: show only Prime-tagged items."
        )
        self.spin_min_score = QSpinBox()
        self.spin_min_score.setRange(0, 100)
        self.spin_min_score.setPrefix("Min Score: ")
        self.spin_min_score.setToolTip("Hides any item whose Score is below this value. Set to 0 to show everything.")
        self.chk_hide_prime_sets = QCheckBox("Hide Prime Sets")
        self.chk_hide_prime_sets.setToolTip(
            "Hides fully-assembled 'X Prime Set' entries, if you only want "
            "to compare individual component prices."
        )
        for widget in (
            self.txt_search,
            self.chk_tradable_only,
            self.spin_min_score,
            self.chk_hide_prime_sets,
        ):
            filter_row.addWidget(widget)
        layout.addLayout(filter_row)

        self.txt_search.textChanged.connect(self._on_search_text_changed)
        self.chk_tradable_only.currentIndexChanged.connect(self._refresh_table)
        self.spin_min_score.valueChanged.connect(self._refresh_table)
        self.chk_hide_prime_sets.stateChanged.connect(self._refresh_table)

        # Debounce the search box: rebuilding a table with thousands of
        # rows on every single keystroke is wasted work and visibly janky.
        # Waiting a short idle moment after the last keystroke before
        # actually refreshing keeps typing responsive on large inventories.
        self._search_debounce_timer = QTimer(self)
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.setInterval(250)
        self._search_debounce_timer.timeout.connect(self._refresh_table)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.loading_indicator = LoadingIndicator()
        layout.addWidget(self.loading_indicator)

        self.table = QTableWidget(0, 10)
        column_headers = [
            "Item", "Qty", "Price", "Total", "Liquidity", "Score",
            "Recommendation", "Ducats", "Wiki", "Sell",
        ]
        column_tooltips = [
            "The item's name. Mods show their fusion rank in parentheses.",
            "How many of this item you own.",
            "Current lowest live-listed price on warframe.market.",
            "Price \u00d7 Qty -- what this whole stack is worth.",
            "How easy this is to actually sell: VERY HIGH moves fast, VERY LOW may sit a while.",
            "A 0-100 rating combining value, liquidity, and quantity. Higher = better sell candidate.",
            "SELL, CONSIDER, or KEEP -- the plain-language summary of Score.",
            "For Prime items with Ducat value: whether Platinum or Ducats is the better deal.",
            "Click to open the item's official Warframe Wiki page, if known.",
            "Click to open the item's warframe.market page, to post a listing yourself.",
        ]
        self.table.setHorizontalHeaderLabels(column_headers)
        for col, tip in enumerate(column_tooltips):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item is not None:
                header_item.setToolTip(tip)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, self.table.columnCount()):
            # ResizeToContents so headers like "Recommendation" always get
            # enough width to display fully instead of being clipped.
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)  # click a column header to sort, like a spreadsheet
        self.table.setToolTip("Click any column header to sort. Click again to reverse the order.")
        self.table.cellClicked.connect(self._on_table_cell_clicked)
        layout.addWidget(self.table)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(ordis.say(ordis.STARTUP))

    # -- Steam launch --------------------------------------------------

    def _on_launch_warframe_clicked(self) -> None:
        self.statusBar().showMessage(ordis.say(ordis.LAUNCH_WARFRAME))
        success = launch_warframe_via_steam()
        if not success:
            self.statusBar().showMessage(ordis.say(ordis.LAUNCH_WARFRAME_FAILED))

    # -- external inventory helper (e.g. warframe-api-helper) -------------

    def _on_grab_inventory_clicked(self) -> None:
        from PySide6.QtWidgets import QApplication

        force_reconfigure = bool(QApplication.keyboardModifiers() & Qt.ShiftModifier)

        helper_path = None if force_reconfigure else load_saved_helper_path()
        if helper_path is None or not helper_path.exists():
            selected, _ = QFileDialog.getOpenFileName(
                self,
                "Locate your inventory helper (e.g. warframe-api-helper.exe)",
                "",
                "Executable Files (*.exe);;All Files (*)",
            )
            if not selected:
                return
            helper_path = Path(selected)
            save_helper_path(helper_path)

        try:
            launch_inventory_helper(helper_path)
        except InventoryHelperLaunchError as exc:
            self._show_error(f"{ordis.say(ordis.GRAB_INVENTORY_FAILED)}\n\n({exc})")
            return

        self.statusBar().showMessage(ordis.say(ordis.GRAB_INVENTORY_LAUNCHED))

        # If the Operator isn't already watching a folder, default to
        # watching the helper's own folder for the inventory.json it writes.
        if not self._watcher.is_active:
            self._watcher.set_watch_dir(helper_path.parent)
            self._watch_timer.start()
            self.btn_watch_folder.setText("STOP WATCHING")

    # -- folder watching -------------------------------------------------

    def _on_watch_folder_clicked(self) -> None:
        if self._watcher.is_active:
            self._watch_timer.stop()
            self._watcher.clear()
            self.btn_watch_folder.setText("WATCH FOLDER")
            self.statusBar().showMessage(ordis.say(ordis.WATCH_STOPPED))
            return

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select the folder where your inventory export is saved "
            "(e.g. wherever warframe-api-helper writes inventory.json)",
        )
        if not directory:
            return

        self._watcher.set_watch_dir(directory)
        self._watch_timer.start()
        self.btn_watch_folder.setText("STOP WATCHING")
        self.statusBar().showMessage(ordis.say(ordis.WATCH_STARTED))
        # Pick up a file that's already sitting there, not just future changes.
        self._on_watch_tick()

    def _on_watch_tick(self) -> None:
        path = self._watcher.poll()
        if path is None:
            return
        self._import_from_path(str(path), auto=True)

    # -- inventory import --------------------------------------------------

    def _load_persisted_inventory(self) -> None:
        snapshot = self._inventory_repo.load()
        if snapshot:
            self._update_summary_labels(snapshot_total=snapshot.total_items)
            self.lbl_last_import.setText(
                f"Last Import: {snapshot.imported_at.strftime('%Y-%m-%d %H:%M')}"
            )

    def _load_persisted_report(self) -> None:
        """Restores the last completed analysis from disk, if any, so the
        table is already filled in on startup instead of staying empty
        until ANALYZE INVENTORY is clicked again."""
        if self._report_repo is None:
            return
        loaded = self._report_repo.load()
        if loaded is None:
            return
        report, analyzed_at_iso = loaded
        self._report = report
        self.lbl_tradable.setText(f"Tradable: {report.total_tradable_items}")
        self.lbl_value.setText(f"Estimated Value: {report.estimated_total_value:.0f}p")
        self.lbl_last_analysis.setText(
            f"Last Analysis: {self._format_iso_timestamp(analyzed_at_iso)} (restored)"
        )
        self._refresh_table()
        self.statusBar().showMessage(
            "Operator, I have restored your last analysis. No need to click "
            "ANALYZE again unless your inventory changed."
        )

    @staticmethod
    def _format_iso_timestamp(iso_str: str) -> str:
        try:
            return datetime.fromisoformat(iso_str).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return iso_str or "unknown time"

    def _on_import_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Inventory", "", "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        self._import_from_path(path, auto=False)

    def _import_from_path(self, path: str, auto: bool) -> None:
        self.statusBar().showMessage(ordis.say(ordis.IMPORT_START))
        try:
            snapshot = self._parser.parse_file(path)
        except InventoryFileNotFoundError:
            self._show_error(ordis.say(ordis.IMPORT_FILE_NOT_FOUND))
            return
        except InvalidInventoryFileError as exc:
            self._show_error(f"{ordis.say(ordis.IMPORT_INVALID_FILE)}\n\n({exc})")
            return

        self._inventory_repo.save(snapshot)
        self._update_summary_labels(snapshot_total=snapshot.total_items)
        self.lbl_last_import.setText(
            f"Last Import: {snapshot.imported_at.strftime('%Y-%m-%d %H:%M')}"
        )

        # A fresh import invalidates any previously restored/completed
        # analysis -- it describes a different inventory now, and leaving
        # the old numbers on screen would be actively misleading rather
        # than just stale.
        self._report = None
        if self._report_repo is not None:
            self._report_repo.clear()
        self.lbl_tradable.setText("Tradable: -")
        self.lbl_value.setText("Estimated Value: -")
        self.lbl_last_analysis.setText("Last Analysis: - (import changed, please re-analyze)")
        self._refresh_table()
        self._update_button_states()

        message = ordis.say(ordis.WATCH_AUTO_IMPORTED) if auto else ordis.say(ordis.IMPORT_SUCCESS)
        if snapshot.unresolved_count:
            message += f" {ordis.say(ordis.IMPORT_UNKNOWN_ITEM)} ({snapshot.unresolved_count} entries could not be identified.)"
        self.statusBar().showMessage(message)

    # -- analysis ------------------------------------------------------

    def _on_analyze_clicked(self) -> None:
        snapshot = self._inventory_repo.snapshot
        if snapshot is None:
            self._show_error("Operator, please import an inventory first. I have nothing to analyze.")
            return

        self.statusBar().showMessage(ordis.say(ordis.ANALYSIS_START))
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # v2.0: Use expanded message pool with 5-second rotation
        message_pool = (
            ordis.ANALYSIS_START + ordis.PROCESSING_FLAVOR + ordis.PROCESSING_ANALYSIS
        )
        self.loading_indicator.start(message_pool, interval_ms=5000)  # 5-second intervals
        
        self.btn_analyze.setEnabled(False)

        force_refresh = self._force_refresh_next_analysis
        self._force_refresh_next_analysis = False

        self._worker = _AnalysisWorker(self._analyzer, snapshot, force_refresh=force_refresh)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_analysis_done)
        self._worker.failed.connect(self._on_analysis_failed)
        self._worker.start()

    def _on_progress(self, current: int, total: int) -> None:
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(current)

    def _on_analysis_done(self, report: PortfolioReport) -> None:
        self._report = report
        self.progress_bar.setVisible(False)
        self.loading_indicator.stop()
        
        # v2.0: Sound effects disabled for now (causes UI freeze)
        # Will be re-enabled in v2.1 with proper threading
        
        self.lbl_tradable.setText(f"Tradable: {report.total_tradable_items}")
        self.lbl_value.setText(f"Estimated Value: {report.estimated_total_value:.0f}p")

        analyzed_at = datetime.now(timezone.utc)
        self.lbl_last_analysis.setText(f"Last Analysis: {analyzed_at.strftime('%Y-%m-%d %H:%M')}")
        if self._report_repo is not None:
            self._report_repo.save(report, analyzed_at.isoformat())
        self._update_button_states()

        message = ordis.say_analysis_summary(
            report.estimated_total_value, report.catalog_matched_count, report.total_inventory_items
        )
        message += (
            f" Matched {report.catalog_matched_count}/{report.total_inventory_items} "
            f"items against the catalog."
        )
        if report.market_error_slug_count:
            message += (
                f" {ordis.say(ordis.MARKET_ERROR)} "
                f"({report.market_error_slug_count} item(s) had no market data at all.)"
            )
        elif report.stale_price_slug_count:
            message += (
                f" {ordis.say(ordis.MARKET_UNAVAILABLE_OFFLINE)} "
                f"({report.stale_price_slug_count} item(s) used slightly stale cached prices.)"
            )
        # No message appended in the normal case -- the report only
        # distinguishes "had to fall back" from "didn't", not "used a
        # still-fresh cache vs. a live call", so there's nothing accurate
        # to say beyond the summary line above when nothing went wrong.

        if any(a.ducats is not None and a.ducats.verdict != DucatVerdict.INSUFFICIENT_DATA for a in report.analyses):
            message += f" {ordis.say(ordis.DUCATS_DONE)}"

        self.statusBar().showMessage(message)
        self._refresh_table()

    def _on_analysis_failed(self, error: str) -> None:
        self.progress_bar.setVisible(False)
        self.loading_indicator.stop()
        self._update_button_states()
        self._show_error(f"{ordis.market_is_being_difficult()}\n\n({error})")

    # -- catalog / market refresh -----------------------------------------

    def _on_update_items_clicked(self) -> None:
        if self._catalog_updater is None:
            self._show_error("Operator, the item catalog isn't wired up in this session.")
            return

        self.statusBar().showMessage(ordis.say(ordis.CATALOG_UPDATE_START))
        # v2.0: Use expanded message pool with 5-second rotation
        message_pool = (
            ordis.CATALOG_UPDATE_START + ordis.PROCESSING_FLAVOR + ordis.PROCESSING_ANALYSIS
        )
        self.loading_indicator.start(message_pool, interval_ms=5000)  # 5-second intervals
        self.btn_update_items.setEnabled(False)

        self._catalog_worker = _CatalogUpdateWorker(
            self._catalog_updater, force=True, name_index_updater=self._name_index_updater
        )
        self._catalog_worker.finished_ok.connect(self._on_update_items_done)
        self._catalog_worker.failed.connect(self._on_update_items_failed)
        self._catalog_worker.start()

    def _on_update_items_done(self, catalog_result, name_index_result) -> None:
        self.loading_indicator.stop()
        self.btn_update_items.setEnabled(True)
        self.lbl_catalog_status.setText(f"Catalog: {catalog_result.entry_count} items known")
        if catalog_result.error and not catalog_result.used_cache:
            message = ordis.say(ordis.CATALOG_UPDATE_FAILED)
        else:
            message = ordis.say(ordis.CATALOG_UPDATE_DONE)
        message += f" ({catalog_result.entry_count} market items known"
        message += ", from cache)" if catalog_result.used_cache else ")"
        if catalog_result.error:
            message += f" Note: {catalog_result.error}"
        if name_index_result is not None:
            self.lbl_names_status.setText(f"Item Names: {name_index_result.entry_count} known")
            message += f" | {name_index_result.entry_count} item names known from Digital Extremes"
            message += ", from cache." if name_index_result.used_cache else "."
            if name_index_result.error:
                message += f" Note: {name_index_result.error}"
            elif 0 < name_index_result.entry_count < 500:
                message += f" {ordis.say(ordis.NAME_INDEX_LOW_COVERAGE)}"
        self.statusBar().showMessage(message)

    def _on_update_items_failed(self, error: str) -> None:
        self.loading_indicator.stop()
        self.btn_update_items.setEnabled(True)
        self._show_error(f"{ordis.say(ordis.CATALOG_UPDATE_FAILED)}\n\n({error})")

    def _on_update_market_clicked(self) -> None:
        snapshot = self._inventory_repo.snapshot
        if snapshot is None:
            self._show_error(
                "Operator, there's no inventory imported yet, so there's nothing "
                "to refresh prices for."
            )
            return

        # Force the next (or an immediate, if one isn't already running) analysis
        # to bypass the price cache and pull fresh order data.
        self._force_refresh_next_analysis = True
        if self._worker is not None and self._worker.isRunning():
            self.statusBar().showMessage(
                "Operator, an analysis is already running -- the next one will use fresh prices."
            )
            return
        self._on_analyze_clicked()

    # -- Wiki links (independent of price/ranking analysis) ---------------

    def _on_update_wiki_clicked(self) -> None:
        if self._wiki_index_builder is None:
            self._show_error("Operator, the Wiki index isn't wired up in this session.")
            return

        names = self._names_needing_wiki_lookup()
        if not names:
            self.statusBar().showMessage(
                "Operator, I have nothing to look up yet -- import and analyze an "
                "inventory first."
            )
            return

        self.statusBar().showMessage(
            f"Consulting the Wiki for {len(set(names))} item name(s), Operator. "
            "This will not affect prices. Names already known from a previous "
            "run are skipped automatically."
        )
        self.loading_indicator.start(["Consulting the Wiki..."] + ordis.PROCESSING_FLAVOR)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_update_wiki.setEnabled(False)

        self._wiki_worker = _WikiUpdateWorker(self._wiki_index_builder, names)
        self._wiki_worker.progress.connect(self._on_progress)
        self._wiki_worker.finished_ok.connect(self._on_update_wiki_done)
        self._wiki_worker.failed.connect(self._on_update_wiki_failed)
        self._wiki_worker.start()

    def _names_needing_wiki_lookup(self) -> list[str]:
        """Item names to resolve, sourced from the current analyzed report
        if one exists, otherwise from whatever is currently imported.
        Only tradable/recognized items have a clean display name worth
        searching the Wiki for -- an unresolved internal path is not.

        Uses base_name (not display_name) deliberately: display_name
        carries a '(Rank N)' suffix for mods, which would make every rank
        of the same mod look like a different item to search for and
        cache separately -- base_name is the shared, clean name so all
        ranks of e.g. Serration correctly share one Wiki lookup."""
        if self._report is not None:
            return [
                a.base_name
                for a in self._report.analyses
                if a.slug is not None and a.base_name
            ]
        return []

    def _on_update_wiki_done(self, result) -> None:
        self.loading_indicator.stop()
        self.progress_bar.setVisible(False)
        self.btn_update_wiki.setEnabled(True)
        self.lbl_wiki_status.setText(f"Wiki Links: {result.total_known} known")
        message = (
            f"Wiki index updated: {result.newly_resolved} new link"
            f"{'s' if result.newly_resolved != 1 else ''} found"
        )
        if result.newly_unresolved:
            message += f", {result.newly_unresolved} had no page"
        if result.skipped_already_known:
            message += f" ({result.skipped_already_known} already known)"
        message += "."
        self.statusBar().showMessage(message)
        self._refresh_table()

    def _on_update_wiki_failed(self, error: str) -> None:
        self.loading_indicator.stop()
        self.progress_bar.setVisible(False)
        self.btn_update_wiki.setEnabled(True)
        self._show_error(f"Operator, the Wiki did not respond.\n\n({error})")


    # -- table / filters -------------------------------------------------

    def _on_search_text_changed(self) -> None:
        self._search_debounce_timer.start()  # restarts the countdown on every keystroke

    def _filtered_sorted(self) -> list[ItemAnalysis]:
        if not self._report:
            return []

        items = list(self._report.analyses)

        query = self.txt_search.text().strip().lower()
        if query:
            items = [a for a in items if query in a.display_name.lower()]

        mode = self.chk_tradable_only.currentText()
        if mode == "Tradable Only":
            items = [a for a in items if a.tradable]
        elif mode == "Prime Only":
            items = [a for a in items if a.is_prime]

        if self.chk_hide_prime_sets.isChecked():
            items = [a for a in items if not is_prime_set_name(a.display_name)]

        min_score = self.spin_min_score.value()
        if min_score > 0:
            items = [a for a in items if a.score >= min_score]

        # No manual sort here anymore -- the table itself is sortable by
        # clicking any column header (see setSortingEnabled(True) above),
        # which is more flexible than one fixed dropdown-driven sort.
        return items

    # Column layout, named for clarity since _refresh_table and
    # _on_table_cell_clicked both need to agree on it.
    _COL_ITEM = 0
    _COL_QTY = 1
    _COL_PRICE = 2
    _COL_TOTAL = 3
    _COL_LIQUIDITY = 4
    _COL_SCORE = 5
    _COL_RECOMMENDATION = 6
    _COL_DUCATS = 7
    _COL_WIKI = 8
    _COL_SELL = 9

    def _refresh_table(self) -> None:
        items = self._filtered_sorted()

        # Disable sorting while repopulating: with setSortingEnabled(True),
        # Qt would otherwise re-sort after every single setItem() call,
        # scrambling rows out from under this loop.
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(items))

        for row, a in enumerate(items):
            item_cell = QTableWidgetItem(a.display_name)
            if not a.data_available and a.error:
                # Flag problem rows visually (not found / not tradable /
                # market fetch failed) rather than leaving the Operator to
                # notice "N/A" scattered across several other columns.
                item_cell.setForeground(QColor(DANGER))
                item_cell.setToolTip(a.error)
            self.table.setItem(row, self._COL_ITEM, item_cell)
            self.table.setItem(
                row, self._COL_QTY, _SortableTableWidgetItem(str(a.quantity), a.quantity)
            )
            self.table.setItem(
                row,
                self._COL_PRICE,
                _SortableTableWidgetItem(
                    f"{a.unit_price:.0f}p" if a.unit_price is not None else "N/A",
                    a.unit_price if a.unit_price is not None else -1,
                ),
            )
            self.table.setItem(
                row,
                self._COL_TOTAL,
                _SortableTableWidgetItem(
                    f"{a.total_value:.0f}p" if a.total_value is not None else "N/A",
                    a.total_value if a.total_value is not None else -1,
                ),
            )

            liquidity_item = _SortableTableWidgetItem(
                a.liquidity_level.value, LIQUIDITY_SORT_RANK.get(a.liquidity_level.value, 0)
            )
            if a.data_available:
                liquidity_item.setToolTip(ordis.say_liquidity(a.liquidity_level))
            self.table.setItem(row, self._COL_LIQUIDITY, liquidity_item)

            self.table.setItem(
                row, self._COL_SCORE, _SortableTableWidgetItem(str(a.score), a.score)
            )

            recommendation_item = _SortableTableWidgetItem(
                a.recommendation.value,
                RECOMMENDATION_SORT_RANK.get(a.recommendation.value, 0),
            )
            if a.data_available:
                recommendation_item.setToolTip(ordis.say_recommendation(a.recommendation))
            self.table.setItem(row, self._COL_RECOMMENDATION, recommendation_item)

            self.table.setItem(row, self._COL_DUCATS, self._make_ducats_cell(a))

            self._set_link_cell(row, self._COL_WIKI, a.wiki_url, "Wiki \u2197")

            sell_url = f"https://warframe.market/items/{a.slug}" if a.slug else None
            self._set_link_cell(row, self._COL_SELL, sell_url, "Sell \u2197")

        self.table.setSortingEnabled(True)

    def _make_ducats_cell(self, analysis: ItemAnalysis) -> QTableWidgetItem:
        """Ducats vs. Platinum comparison, when there's enough data for
        one. This was being computed for every item all along
        (DucatAnalyzer runs as part of every analysis) but was never
        actually shown anywhere -- a real gap found during cleanup."""
        ducats = analysis.ducats
        if ducats is None or ducats.verdict == DucatVerdict.INSUFFICIENT_DATA:
            return _SortableTableWidgetItem("-", -1)

        text = f"{ducats.ducats}d @ {ducats.plat_per_ducat:.2f}p ({ducats.verdict.value})"
        item = _SortableTableWidgetItem(text, ducats.plat_per_ducat)
        if ducats.verdict == DucatVerdict.SELL_FOR_PLAT:
            item.setToolTip("Better value in Platinum than Baro's Ducat rate.")
        else:
            item.setToolTip("Better value kept for Ducats than sold for Platinum.")
        return item

    def _set_link_cell(self, row: int, col: int, url: Optional[str], label: str) -> None:
        """Renders a clickable-looking link cell using a plain
        QTableWidgetItem (not setCellWidget) with the URL stashed in
        Qt.UserRole -- this keeps the cell fully compatible with
        setSortingEnabled(True), since Qt moves QTableWidgetItem data
        together with its row on sort, but does NOT do the same for
        cell widgets (a real Qt gotcha: a widget set via setCellWidget
        stays pinned to its row/column index and would end up on the
        wrong row after a sort)."""
        if url:
            item = QTableWidgetItem(label)
            item.setData(Qt.UserRole, url)
            item.setForeground(_link_color())
            font = item.font()
            font.setUnderline(True)
            item.setFont(font)
            item.setToolTip(url)
        else:
            item = QTableWidgetItem("-")
        self.table.setItem(row, col, item)

    def _on_table_cell_clicked(self, row: int, col: int) -> None:
        if col not in (self._COL_WIKI, self._COL_SELL):
            return
        item = self.table.item(row, col)
        if item is None:
            return
        url = item.data(Qt.UserRole)
        if url:
            QDesktopServices.openUrl(QUrl(url))


    # -- export ------------------------------------------------------

    def _on_export_clicked(self) -> None:
        if not self._report:
            self._show_error("Operator, there is nothing to export yet. Try analyzing first.")
            return

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Analysis",
            "ordis_market_export.csv",
            "CSV (*.csv);;JSON (*.json);;Excel (*.xlsx)",
        )
        if not path:
            return

        try:
            if path.endswith(".json"):
                exporter.export_json(self._report, path)
            elif path.endswith(".xlsx"):
                exporter.export_xlsx(self._report, path)
            else:
                exporter.export_csv(self._report, path)
        except exporter.ExportError as exc:
            self._show_error(str(exc))
            return

        self.statusBar().showMessage(ordis.say(ordis.EXPORT_DONE))

    # -- helpers ------------------------------------------------------

    def _update_summary_labels(self, snapshot_total: int) -> None:
        self.lbl_total_items.setText(f"Total Items: {snapshot_total}")

    def _update_button_states(self) -> None:
        """Enables/disables buttons based on what's actually ready, so the
        Operator can tell at a glance what to do next instead of clicking
        things that can't do anything yet. Called after every state change
        (import, analysis, startup restore) rather than left for the
        Operator to discover via an error message after the fact."""
        has_inventory = self._inventory_repo.snapshot is not None
        has_report = self._report is not None

        self.btn_analyze.setEnabled(has_inventory)
        self.btn_analyze.setToolTip(
            "Cross-references your inventory with live market prices."
            if has_inventory
            else "Import an inventory first (IMPORT INVENTORY, GRAB INVENTORY, or WATCH FOLDER)."
        )

        self.btn_update_market.setEnabled(has_inventory)
        self.btn_update_market.setToolTip(
            "Re-runs analysis, ignoring the price cache, for fresher numbers."
            if has_inventory
            else "Import an inventory first -- there's nothing to price yet."
        )

        self.btn_export.setEnabled(has_report)
        self.btn_export.setToolTip(
            "Saves the current analysis to CSV, JSON, or XLSX."
            if has_report
            else "Run ANALYZE INVENTORY first -- there's nothing to export yet."
        )

        self.btn_update_wiki.setEnabled(has_report)
        self.btn_update_wiki.setToolTip(
            "Looks up official Warframe Wiki links for items in your current "
            "inventory/report. Runs independently of price analysis and never "
            "slows it down."
            if has_report
            else "Run ANALYZE INVENTORY first -- Wiki links are resolved for whatever's in the report."
        )

    def _show_error(self, message: str) -> None:
        logger.warning(message)
        QMessageBox.warning(self, "Ordis Market", message)
