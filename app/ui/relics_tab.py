"""
ui.relics_tab
=============

The "Relics" tab: Prime sets you hold parts of, and which of your own relics
could drop the parts you're missing.

Everything here runs on the UI thread except the relic-data download, which
is a QThread handed to MainWindow (so closing the window stops it safely).

Ordis: "Open them in order, Operator. Or not. The relics are patient. I am
        less so."
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Iterable, Optional

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.inventory.models import InventoryItem
from app.relics.analyzer import RelicsReport, SetState, SetStatus, analyze_relics
from app.relics.models import RelicData
from app.relics.store import RelicDataStore
from app.relics.view import (
    FilterMode,
    detail_text,
    filter_statuses,
    missing_text,
    open_text,
    parts_text,
    state_rank,
)
from app.ui.sound_manager import get_sound_manager
from app.ui.theme import ACCENT_CYAN, ACCENT_GOLD, DANGER, TEXT_MUTED

logger = logging.getLogger(__name__)

_STATE_COLORS = {
    SetState.COMPLETE: QColor(ACCENT_CYAN),
    SetState.COMPLETABLE: QColor(ACCENT_GOLD),
    SetState.PARTIAL: QColor(TEXT_MUTED),
    SetState.NONE: QColor(TEXT_MUTED),
}


class _SortItem(QTableWidgetItem):
    """Table cell that sorts by a number instead of by its text."""

    def __init__(self, text: str, sort_value: float) -> None:
        super().__init__(text)
        self._sort_value = sort_value

    def __lt__(self, other: object) -> bool:  # noqa: D105 - Qt override
        if isinstance(other, _SortItem):
            return self._sort_value < other._sort_value
        return super().__lt__(other)  # type: ignore[operator]


class _RelicDataWorker(QThread):
    """Downloads and caches the relic dataset off the UI thread."""

    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, store: RelicDataStore) -> None:
        super().__init__()
        self._store = store

    def run(self) -> None:
        try:
            self.finished_ok.emit(self._store.refresh())
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            logger.exception("Relic data update failed")
            self.failed.emit(str(exc))


class RelicsTab(QWidget):
    _COLUMNS = ("Set", "Parts", "Status", "Missing", "Relics to open")
    _COLUMN_TIPS = (
        "The Prime set (warframe, weapon, archwing, companion...).",
        "Parts you own out of the parts the set needs. Warframe parts count as owned "
        "whether you hold the Blueprint (the diagram) or the built Component.",
        "Complete: nothing missing. Completable: every missing part drops from a relic "
        "you own. Partial: only some do.",
        "Parts you still need (×N = needs more than one copy).",
        "Which of your relics to crack, best coverage first. Format: relic ×how many "
        "you own → the parts it can drop.",
    )

    def __init__(
        self,
        store: RelicDataStore,
        get_items: Callable[[], Iterable[InventoryItem]],
        start_worker: Callable[[QThread], None],
        show_message: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._get_items = get_items
        self._start_worker = start_worker
        self._show_message = show_message
        self._data: Optional[RelicData] = None
        self._report: Optional[RelicsReport] = None
        self._worker: Optional[_RelicDataWorker] = None
        self._cache_loaded = False
        self._auto_download_tried = False
        self._last_error: Optional[str] = None
        self._rows: list[SetStatus] = []

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._render)

        self._build_ui()

    # -- construction ---------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        intro = QLabel(
            "Prime sets you hold parts of, and which of your own relics could drop "
            "the parts you're missing."
        )
        intro.setObjectName("AppSubtitle")
        intro.setWordWrap(True)
        intro.setToolTip(
            "Built from your imported inventory (parts and relics) and the public relic drop tables."
        )
        layout.addWidget(intro)

        top = QHBoxLayout()
        self.lbl_status = QLabel("Relic data: not loaded")
        self.lbl_status.setObjectName("SummaryLabel")
        self.lbl_status.setToolTip("What relic drop data is loaded, and how old it is.")
        top.addWidget(self.lbl_status, stretch=1)
        self.btn_update = QPushButton("UPDATE RELIC DATA")
        self.btn_update.setToolTip(
            "Downloads the current relic drop tables (about 10 MB, from the WFCD "
            "warframe-items dataset on GitHub) and caches them. Do this when new Primes release."
        )
        self.btn_update.clicked.connect(self.start_update)
        top.addWidget(self.btn_update)
        layout.addLayout(top)

        filters = QHBoxLayout()
        self._modes = list(FilterMode)  # combo index -> mode (a str-Enum would come back from Qt as plain text)
        self.cmb_mode = QComboBox()
        for mode in self._modes:
            self.cmb_mode.addItem(mode.value)
        self.cmb_mode.setToolTip("Which sets to list.")
        self.cmb_mode.currentIndexChanged.connect(self._render)
        filters.addWidget(self.cmb_mode)
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search sets...")
        self.txt_search.setToolTip("Type part of a set's name, e.g. 'gyre' or 'akbolto'.")
        self.txt_search.textChanged.connect(lambda _text: self._search_timer.start())
        filters.addWidget(self.txt_search, stretch=1)
        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("SummaryLabel")
        self.lbl_count.setToolTip("How many sets match the current filter.")
        filters.addWidget(self.lbl_count)
        layout.addLayout(filters)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # busy indicator: size of the download isn't known up front
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.lbl_hint = QLabel("")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setVisible(False)
        layout.addWidget(self.lbl_hint)

        self.table = QTableWidget(0, len(self._COLUMNS))
        self.table.setHorizontalHeaderLabels(list(self._COLUMNS))
        for col, tip in enumerate(self._COLUMN_TIPS):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item is not None:
                header_item.setToolTip(tip)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setSortingEnabled(True)
        # No column is "sorted" until the user clicks a header, so rows keep the
        # priority order from relics.view (most completable first).
        header.setSortIndicator(-1, Qt.AscendingOrder)
        self.table.setToolTip("Click a set to see every part and the exact drop odds below.")
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table, stretch=3)

        self.txt_detail = QTextEdit()
        self.txt_detail.setReadOnly(True)
        self.txt_detail.setMinimumHeight(150)
        self.txt_detail.setToolTip(
            "Breakdown of the selected set: each part, and which of your relics can drop it, "
            "with the chance per opening and the chance if you open all the copies you own."
        )
        layout.addWidget(self.txt_detail, stretch=2)

    # -- data -----------------------------------------------------------------

    def on_activated(self) -> None:
        """Called when the tab is shown: load the cache, show results, and
        download the data once if there is none yet."""
        if not self._cache_loaded:
            self._cache_loaded = True
            self._data = self._store.load()
        self.reload()
        if self._data is None and not self._auto_download_tried:
            self._auto_download_tried = True
            self.start_update()

    def reload(self) -> None:
        """Recomputes from the current inventory (call after an import)."""
        if not self._cache_loaded:
            return  # the tab hasn't been opened yet; on_activated will do it
        items = list(self._get_items())
        self._report = analyze_relics(items, self._data) if self._data and items else None
        self._update_status_label()
        self._render()

    def start_update(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self.btn_update.setEnabled(False)
        self.progress.setVisible(True)
        self.lbl_status.setText("Relic data: downloading (about 10 MB)...")
        self._worker = _RelicDataWorker(self._store)
        self._worker.finished_ok.connect(self._on_update_done)
        self._worker.failed.connect(self._on_update_failed)
        self._start_worker(self._worker)

    def _on_update_done(self, data: RelicData) -> None:
        self._data = data
        self._last_error = None
        self._cache_loaded = True
        self.progress.setVisible(False)
        self.btn_update.setEnabled(True)
        get_sound_manager().play_notification()
        self._show_message(
            f"Relic data updated, Operator: {len(data.relics)} relics, {len(data.sets)} Prime sets."
        )
        self.reload()

    def _on_update_failed(self, error: str) -> None:
        self._last_error = error
        self.progress.setVisible(False)
        self.btn_update.setEnabled(True)
        get_sound_manager().play_error()
        self._show_message(f"Operator, I could not fetch the relic tables. ({error})")
        self._update_status_label(error=error)
        self._render()

    # -- rendering ------------------------------------------------------------

    def _update_status_label(self, error: Optional[str] = None) -> None:
        if self._data is None:
            text = "Relic data: not downloaded"
            if error or self._last_error:
                text += " (download failed)"
        else:
            when = datetime.fromtimestamp(self._data.fetched_at).strftime("%Y-%m-%d")
            text = f"Relic data: {len(self._data.relics)} relics, {len(self._data.sets)} sets, updated {when}"
            if self._store.is_stale(self._data):
                text += " (over a week old -- UPDATE for new Primes)"
        if self._report is not None:
            text += (
                f" | You own {self._report.owned_relic_total} relics "
                f"({self._report.owned_relic_kinds} different)"
            )
        self.lbl_status.setText(text)

    def _hint(self) -> str:
        if self._data is None:
            return (
                "Operator, I have no relic tables yet. Click UPDATE RELIC DATA "
                "(it also happens automatically the first time you open this tab)."
            )
        if self._report is None:
            return "Import an inventory first (IMPORT INVENTORY, GRAB INVENTORY or WATCH FOLDER on the Market tab)."
        if not self._report.owned_relic_total:
            return (
                "I found no relics in this inventory. The sets below can only list parts you "
                "hold; with no relics there is nothing to open."
            )
        return ""

    def _current_mode(self) -> FilterMode:
        index = self.cmb_mode.currentIndex()
        return self._modes[index] if 0 <= index < len(self._modes) else FilterMode.COMPLETABLE

    def _render(self) -> None:
        hint = self._hint()
        self.lbl_hint.setText(hint)
        self.lbl_hint.setVisible(bool(hint))

        statuses = (
            filter_statuses(self._report.sets, self._current_mode(), self.txt_search.text())
            if self._report is not None
            else []
        )
        self._rows = statuses
        self.lbl_count.setText(f"{len(statuses)} sets")

        selected_name = self._selected_set_name()
        self.table.setSortingEnabled(False)  # otherwise Qt re-sorts after every setItem()
        self.table.setRowCount(len(statuses))
        for row, status in enumerate(statuses):
            progress = status.owned_units / status.need_units if status.need_units else 0.0
            name_item = QTableWidgetItem(status.prime_set.name)
            name_item.setData(Qt.UserRole, status.prime_set.name)
            state_item = _SortItem(status.state.value, state_rank(status.state))
            state_item.setForeground(_STATE_COLORS[status.state])
            missing = missing_text(status)
            relics = open_text(status)
            relics_item = QTableWidgetItem(relics)
            if "no relic of yours" in relics:
                relics_item.setForeground(QColor(DANGER))
            relics_item.setToolTip(relics)
            missing_item = QTableWidgetItem(missing)
            missing_item.setToolTip(missing)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, _SortItem(parts_text(status), progress))
            self.table.setItem(row, 2, state_item)
            self.table.setItem(row, 3, missing_item)
            self.table.setItem(row, 4, relics_item)
        self.table.setSortingEnabled(True)
        self.table.resizeRowsToContents()

        self._restore_selection(selected_name)
        self._on_selection_changed()

    def _selected_set_name(self) -> Optional[str]:
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return item.data(Qt.UserRole) if item is not None else None

    def _restore_selection(self, set_name: Optional[str]) -> None:
        target = 0
        if set_name is not None:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item is not None and item.data(Qt.UserRole) == set_name:
                    target = row
                    break
        if self.table.rowCount():
            self.table.selectRow(target)

    def _on_selection_changed(self) -> None:
        name = self._selected_set_name()
        if name is None:
            self.txt_detail.setPlainText("")
            return
        status = next((s for s in self._rows if s.prime_set.name == name), None)
        self.txt_detail.setPlainText(detail_text(status) if status is not None else "")
