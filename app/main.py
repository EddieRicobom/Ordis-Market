"""
main
====

Application entry point. Wires together config, repositories, the market
client, and the UI.

Ordis: "Initializing. Please stand by while I reassemble myself, as I do
        every single time you start this program."
"""

from __future__ import annotations

import json
import sys

from app.analysis.portfolio import PortfolioAnalyzer
from app.analysis.report_repository import ReportRepository
from app.cache.cache_store import PriceCache
from app.catalog.catalog import ItemCatalog
from app.catalog.name_index import NameIndex
from app.catalog.updater import ItemCatalogUpdater, NameIndexUpdater
from app.catalog.wiki_index import WikiIndex
from app.catalog.wiki_index_builder import WikiIndexBuilder
from app.config.settings import (
    AppSettings,
    CACHE_DIR,
    DATA_DIR,
    FELL_BACK_TO_USER_DIR,
    MARKET_RATE_LIMIT_PER_SECOND,
    ROOT_DIR,
)
from app.integrations.wiki_client import WikiClient
from app.inventory.parser import InventoryParser
from app.inventory.repository import InventoryRepository
from app.logging_setup import configure_logging
from app.market.client import ClientConfig, WarframeMarketClient
from app.market.repository import MarketRepository


def load_settings() -> AppSettings:
    settings_path = DATA_DIR / "settings.json"
    if settings_path.exists():
        try:
            return AppSettings.from_dict(json.loads(settings_path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return AppSettings()


def main() -> int:
    logger = configure_logging()
    if FELL_BACK_TO_USER_DIR:
        logger.warning(
            "Could not write next to the application's own folder (likely a "
            "permissions issue) -- using %s instead. Move OrdisMarket to a "
            "folder you have write access to if you'd rather keep data "
            "alongside it.",
            ROOT_DIR,
        )
    settings = load_settings()

    market_client = WarframeMarketClient(
        ClientConfig(requests_per_second=MARKET_RATE_LIMIT_PER_SECOND)
    )
    price_cache = PriceCache(CACHE_DIR / "orders", ttl_seconds=settings.cache_ttl_seconds)
    market_repo = MarketRepository(market_client, price_cache, offline_mode=settings.offline_mode)

    catalog = ItemCatalog(DATA_DIR / "catalog.json")
    catalog_updater = ItemCatalogUpdater(
        catalog, market_client, DATA_DIR / "catalog_meta.txt", settings.catalog_ttl_seconds
    )
    catalog_result = catalog_updater.ensure_fresh()
    logger.info(
        "Catalog ready: %s entries (updated=%s, cache=%s)",
        catalog_result.entry_count,
        catalog_result.updated,
        catalog_result.used_cache,
    )

    name_index = NameIndex(DATA_DIR / "name_index.json")
    name_index_updater = NameIndexUpdater(
        name_index, DATA_DIR / "name_index_meta.txt", settings.name_index_ttl_seconds
    )
    name_index_result = name_index_updater.ensure_fresh()
    logger.info(
        "Name index ready: %s entries (updated=%s, cache=%s, error=%s)",
        name_index_result.entry_count,
        name_index_result.updated,
        name_index_result.used_cache,
        name_index_result.error,
    )

    inventory_parser = InventoryParser()
    inventory_repo = InventoryRepository(DATA_DIR / "inventory.json")
    report_repo = ReportRepository(DATA_DIR / "last_analysis.json")

    wiki_index = WikiIndex(DATA_DIR / "wiki_index.json")
    wiki_index.load_from_disk()
    wiki_index_builder = WikiIndexBuilder(wiki_index, WikiClient())
    logger.info("Wiki index loaded: %s known links", len(wiki_index))

    portfolio_analyzer = PortfolioAnalyzer(
        catalog, market_repo, settings, name_index=name_index, wiki_index=wiki_index
    )

    try:
        from PySide6.QtWidgets import QApplication

        from app.ui.main_window import MainWindow
    except ImportError:
        # Whoever launched us skipped run.py (e.g. `python -m app.main`
        # directly) -- give dependency auto-install one more chance before
        # giving up, so this entry point is self-sufficient too.
        from app.bootstrap import ensure_dependencies

        logger.warning("PySide6 not found on import. Attempting automatic install...")
        result = ensure_dependencies()
        if not result.ok:
            logger.error(
                "PySide6 could not be installed automatically (%s). "
                "Run: pip install -r requirements.txt",
                ", ".join(result.failed),
            )
            print(
                "Ordis Market requires PySide6 to show the dashboard, and "
                "automatic installation failed.\n"
                "Install dependencies manually with: pip install -r requirements.txt"
            )
            return 1

        from PySide6.QtWidgets import QApplication  # noqa: F811

        from app.ui.main_window import MainWindow  # noqa: F811

    app = QApplication(sys.argv)

    from app.ui.theme import apply_theme

    apply_theme(app)

    window = MainWindow(
        inventory_parser,
        inventory_repo,
        portfolio_analyzer,
        catalog_updater,
        name_index_updater,
        wiki_index_builder,
        report_repo,
        initial_catalog_count=catalog_result.entry_count,
        initial_name_index_count=name_index_result.entry_count,
        initial_wiki_count=len(wiki_index),
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
