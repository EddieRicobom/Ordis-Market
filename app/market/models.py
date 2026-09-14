"""
market.models
=============

Data structures describing warframe.market data as consumed by
Ordis Market. These are a deliberately small subset of the full v2 API
data model (see https://docs.warframe.market/docs/data-models) -- only
the fields the pricing/liquidity/sell-score engines actually need.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class MarketOrder:
    """A single visible order for an item."""

    order_type: OrderType
    platinum: float
    quantity: int
    user_online: bool = True
    user_status: str = "unknown"  # "ingame" | "online" | "offline"
    mod_rank: Optional[int] = None
    """The mod's fusion rank this order is listed at, when the item is a
    mod (warframe.market lets sellers specify this per-order). None for
    non-mod items, or when the order simply didn't include the field."""


@dataclass(frozen=True)
class MarketItem:
    """Catalog-level info about a tradable item, as known to
    warframe.market (not the same as the wiki/export catalog, but
    overlapping)."""

    slug: str
    item_id: str
    name: str
    tradable: bool = True
    ducats: Optional[int] = None
    set_slug: Optional[str] = None  # slug of the parent set, if this is a component
    is_set: bool = False
    component_slugs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ItemOrders:
    """All fetched orders for one item, plus request metadata."""

    slug: str
    sell_orders: tuple[MarketOrder, ...]
    buy_orders: tuple[MarketOrder, ...]
    fetched_at: float  # unix timestamp
