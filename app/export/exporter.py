"""
export.exporter
================

Exports a PortfolioReport to CSV, JSON, or XLSX.

Ordis: "Export complete! I have placed your financial secrets into a
        spreadsheet. Please guard this information carefully. Or don't.
        I am merely software."
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.analysis.portfolio import PortfolioReport
from app.market.ducats import DucatVerdict


_HEADERS = [
    "Item",
    "Quantity",
    "Price",
    "TotalValue",
    "Liquidity",
    "SellScore",
    "Recommendation",
    "Ducats",
    "PlatPerDucat",
    "DucatVerdict",
    "WikiURL",
]


def _rows(report: PortfolioReport) -> list[list]:
    rows = []
    for a in report.analyses:
        has_ducats = a.ducats is not None and a.ducats.verdict != DucatVerdict.INSUFFICIENT_DATA
        rows.append(
            [
                a.display_name,
                a.quantity,
                a.unit_price if a.unit_price is not None else "",
                a.total_value if a.total_value is not None else "",
                a.liquidity_level.value,
                a.score,
                a.recommendation.value,
                a.ducats.ducats if has_ducats else "",
                a.ducats.plat_per_ducat if has_ducats else "",
                a.ducats.verdict.value if a.ducats is not None else "",
                a.wiki_url or "",
            ]
        )
    return rows


class ExportError(Exception):
    """Raised when export fails, e.g. missing optional dependency."""


def export_csv(report: PortfolioReport, path: str | Path) -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(_HEADERS)
        writer.writerows(_rows(report))
    return out_path


def export_json(report: PortfolioReport, path: str | Path) -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": {
            "total_inventory_items": report.total_inventory_items,
            "total_tradable_items": report.total_tradable_items,
            "estimated_total_value": report.estimated_total_value,
            "unresolved_count": report.unresolved_count,
        },
        "items": [
            dict(zip([h.lower() for h in _HEADERS], row)) for row in _rows(report)
        ],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def export_xlsx(report: PortfolioReport, path: str | Path) -> Path:
    try:
        from openpyxl import Workbook
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ExportError(
            "XLSX export requires the 'openpyxl' package. "
            "Ordis recommends: pip install openpyxl"
        ) from exc

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ordis Market Export"
    sheet.append(_HEADERS)
    for row in _rows(report):
        sheet.append(row)

    workbook.save(out_path)
    return out_path
