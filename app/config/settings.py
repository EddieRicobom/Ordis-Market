"""
config.settings
================

Central, boring, professional configuration. Ordis is not allowed in here
except in comments, because Operators deserve a config file they can trust.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


APP_VERSION = "1.0.0"

# Warframe.market rules require a descriptive, honest User-Agent.
# See: https://docs.warframe.market/docs/rules/overview
USER_AGENT = f"OrdisMarket/{APP_VERSION} (+https://github.com/ordis-market/ordis-market)"

# Public v2 HTTP API base, per https://docs.warframe.market/docs/api/overview
MARKET_API_BASE = "https://api.warframe.market/v2"

# General public rate limit per warframe.market's published rules:
# "The general public API limit is 3 requests per second."
MARKET_RATE_LIMIT_PER_SECOND = 3


def _primary_root_dir() -> Path:
    """Where Ordis Market's data would *ideally* live: next to the real
    .exe when frozen (see the frozen-mode note below), or the actual
    project folder when run from source."""
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller-frozen executable. Modules bundled
        # inside a --onefile .exe are extracted to a temporary folder at
        # runtime (deleted again on exit), so a __file__-based path would
        # silently wipe the catalog, caches, last-imported inventory, and
        # last analysis on every single launch -- anchoring next to the
        # actual .exe instead is what makes those actually persist.
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _fallback_root_dir() -> Path:
    """A per-user writable location, used only if the primary location
    (next to the .exe/project) turns out not to be writable -- e.g. the
    Operator placed OrdisMarket.exe somewhere like Program Files without
    admin rights. Prefers the OS's own per-user app-data convention;
    falls back to a dotfolder under the home directory if that env var
    isn't set (non-Windows, or an unusual environment)."""
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "OrdisMarket"
    return Path.home() / ".ordis-market"


def _prepare_data_dirs(
    primary_root: Optional[Path] = None,
) -> tuple[Path, Path, Path, Path, bool]:
    """Creates (and returns) the data/cache/log directories, falling back
    to a per-user writable location if the primary one can't be written
    to (permission denied is the realistic case here -- e.g. an .exe
    placed in a protected system folder). Returns (root, data, cache,
    log, used_fallback) rather than raising, so a bad install location
    degrades gracefully instead of crashing the app before it can even
    show a window.
    """
    root = primary_root if primary_root is not None else _primary_root_dir()
    used_fallback = False

    def _try_create(candidate_root: Path) -> Optional[tuple[Path, Path, Path]]:
        data = candidate_root / "data"
        cache = data / "cache"
        log = candidate_root / "logs"
        try:
            data.mkdir(parents=True, exist_ok=True)
            cache.mkdir(parents=True, exist_ok=True)
            log.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
        return data, cache, log

    result = _try_create(root)
    if result is None:
        used_fallback = True
        root = _fallback_root_dir()
        result = _try_create(root)
        if result is None:
            # Even the per-user fallback failed -- there is genuinely
            # nowhere sensible left to write, so let this raise loudly
            # and visibly rather than silently improvising something.
            data = root / "data"
            (data / "cache").mkdir(parents=True, exist_ok=True)
            (root / "logs").mkdir(parents=True, exist_ok=True)
            result = (data, data / "cache", root / "logs")

    data_dir, cache_dir, log_dir = result
    return root, data_dir, cache_dir, log_dir, used_fallback


# Root data directories. FELL_BACK_TO_USER_DIR lets main.py log a clear,
# diagnosable note if this ever actually happens, instead of the
# Operator just quietly ending up with data in an unexpected place.
ROOT_DIR, DATA_DIR, CACHE_DIR, LOG_DIR, FELL_BACK_TO_USER_DIR = _prepare_data_dirs()


class PricingStrategy(str, Enum):
    LOWEST = "LOWEST"
    AVERAGE = "AVERAGE"
    MEDIAN = "MEDIAN"
    RECOMMENDED = "RECOMMENDED"


class Platform(str, Enum):
    PC = "pc"
    PS4 = "ps4"
    XBOX = "xbox"
    SWITCH = "switch"


@dataclass
class AppSettings:
    """Runtime-adjustable settings. Persisted to data/settings.json."""

    platform: Platform = Platform.PC
    pricing_strategy: PricingStrategy = PricingStrategy.LOWEST
    """Default is LOWEST -- the current lowest live-listed price. Ordis
    Market intentionally does not offer a '3-day median' option: warframe.
    market's supported v2 API only exposes live orders, not historical
    closed-trade data (that only exists on the deprecated, unsupported v1
    API), so a true historical median isn't something this app can source
    honestly. RECOMMENDED/AVERAGE/MEDIAN remain available as alternate
    live-order-based strategies for anyone who wants them."""
    ducat_reference_value: float = 8.0  # plat-per-ducat "worth it" reference
    cache_ttl_seconds: int = 60 * 30  # 30 minutes for order data
    catalog_ttl_seconds: int = 60 * 60 * 24  # 24 hours for the item catalog
    name_index_ttl_seconds: int = 60 * 60 * 24  # 24 hours for the DE name-mapping data
    offline_mode: bool = False
    request_timeout_seconds: float = 10.0

    def to_dict(self) -> dict:
        return {
            "platform": self.platform.value,
            "pricing_strategy": self.pricing_strategy.value,
            "ducat_reference_value": self.ducat_reference_value,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "catalog_ttl_seconds": self.catalog_ttl_seconds,
            "name_index_ttl_seconds": self.name_index_ttl_seconds,
            "offline_mode": self.offline_mode,
            "request_timeout_seconds": self.request_timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        return cls(
            platform=Platform(data.get("platform", Platform.PC.value)),
            pricing_strategy=PricingStrategy(
                data.get("pricing_strategy", PricingStrategy.LOWEST.value)
            ),
            ducat_reference_value=float(data.get("ducat_reference_value", 8.0)),
            cache_ttl_seconds=int(data.get("cache_ttl_seconds", 1800)),
            catalog_ttl_seconds=int(data.get("catalog_ttl_seconds", 86400)),
            name_index_ttl_seconds=int(data.get("name_index_ttl_seconds", 86400)),
            offline_mode=bool(data.get("offline_mode", False)),
            request_timeout_seconds=float(data.get("request_timeout_seconds", 10.0)),
        )
