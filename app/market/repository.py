"""
market.repository
==================

MarketRepository is the single place the rest of the app asks for order
data. It transparently combines the live WarframeMarketClient with the
PriceCache, and degrades gracefully to stale cached data when offline.

Ordis: "You ask me for a price. I do not care whether it came from the
        market just now or from what I remembered five minutes ago -- I
        will tell you which one it is, so you can decide if you trust it."
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.cache.cache_store import PriceCache
from app.market.client import MarketClientError, WarframeMarketClient
from app.market.models import ItemOrders, MarketOrder, OrderType


@dataclass
class OrdersResult:
    item_orders: Optional[ItemOrders]
    from_cache: bool
    stale: bool
    error: Optional[str] = None


def _orders_to_json(item_orders: ItemOrders) -> dict:
    def order_dict(o: MarketOrder) -> dict:
        return {
            "order_type": o.order_type.value,
            "platinum": o.platinum,
            "quantity": o.quantity,
            "user_online": o.user_online,
            "user_status": o.user_status,
        }

    return {
        "slug": item_orders.slug,
        "sell_orders": [order_dict(o) for o in item_orders.sell_orders],
        "buy_orders": [order_dict(o) for o in item_orders.buy_orders],
        "fetched_at": item_orders.fetched_at,
    }


def _orders_from_json(payload: dict) -> ItemOrders:
    def order_from(raw: dict) -> MarketOrder:
        return MarketOrder(
            order_type=OrderType(raw["order_type"]),
            platinum=raw["platinum"],
            quantity=raw["quantity"],
            user_online=raw["user_online"],
            user_status=raw["user_status"],
        )

    return ItemOrders(
        slug=payload["slug"],
        sell_orders=tuple(order_from(o) for o in payload["sell_orders"]),
        buy_orders=tuple(order_from(o) for o in payload["buy_orders"]),
        fetched_at=payload["fetched_at"],
    )


class MarketRepository:
    def __init__(
        self,
        client: WarframeMarketClient,
        cache: PriceCache,
        offline_mode: bool = False,
    ) -> None:
        self._client = client
        self._cache = cache
        self.offline_mode = offline_mode

    def get_orders(self, slug: str, force_refresh: bool = False) -> OrdersResult:
        cache_key = f"orders_{slug}"

        if not force_refresh and not self.offline_mode:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return OrdersResult(
                    item_orders=_orders_from_json(cached), from_cache=True, stale=False
                )

        if self.offline_mode:
            stale = self._cache.get_stale(cache_key)
            if stale is not None:
                return OrdersResult(
                    item_orders=_orders_from_json(stale), from_cache=True, stale=True
                )
            return OrdersResult(
                item_orders=None,
                from_cache=False,
                stale=False,
                error="No cached data available while offline.",
            )

        try:
            item_orders = self._client.get_orders_for_item(slug)
        except MarketClientError as exc:
            stale = self._cache.get_stale(cache_key)
            if stale is not None:
                return OrdersResult(
                    item_orders=_orders_from_json(stale),
                    from_cache=True,
                    stale=True,
                    error=str(exc),
                )
            return OrdersResult(item_orders=None, from_cache=False, stale=False, error=str(exc))

        self._cache.set(cache_key, _orders_to_json(item_orders))
        return OrdersResult(item_orders=item_orders, from_cache=False, stale=False)
