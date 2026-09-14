"""
market.client
=============

WarframeMarketClient talks to the public warframe.market v2 HTTP API.

Ordis: "I am going to ask the market some questions now, Operator. I will
        be polite. I will also be fast, because you deserve answers, but
        not so fast that they start ignoring me again."

Design notes (see RESEARCH.md for sources):

* Base URL: https://api.warframe.market/v2  (the legacy /v1/ API is
  deprecated and unsupported per warframe.market's own docs, so this
  client targets v2 exclusively).
* Required etiquette per warframe.market's published rules:
    - identify ourselves with a descriptive User-Agent
    - respect the published rate limit (3 requests/second, general)
    - cache aggressively and avoid tight polling loops
* No authentication is used or required for read-only price/catalog
  lookups -- this client never signs in, never places orders, and never
  touches an Operator's warframe.market account.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import requests

from app.common.rate_limiter import RateLimiter
from app.common.http import make_session
from app.config.settings import MARKET_API_BASE, MARKET_RATE_LIMIT_PER_SECOND, USER_AGENT
from app.market.models import ItemOrders, MarketOrder, OrderType


class MarketClientError(Exception):
    """Base class for market client failures. Ordis files these under
    'the merchants are being difficult'."""


class MarketRateLimitedError(MarketClientError):
    """Raised when the market responds with HTTP 429 after exhausting
    our retry budget."""


class MarketUnavailableError(MarketClientError):
    """Raised for network failures, timeouts, or 5xx responses."""


class MarketNotFoundError(MarketClientError):
    """Raised when the requested item slug does not exist on the market."""


@dataclass
class ClientConfig:
    base_url: str = MARKET_API_BASE
    user_agent: str = USER_AGENT
    requests_per_second: float = MARKET_RATE_LIMIT_PER_SECOND
    timeout_seconds: float = 10.0
    max_retries: int = 3
    backoff_base_seconds: float = 1.0


class WarframeMarketClient:
    """Read-only client for warframe.market's public v2 API."""

    def __init__(self, config: Optional[ClientConfig] = None, session: Optional[requests.Session] = None) -> None:
        self._config = config or ClientConfig()
        self._session = session or make_session()
        # ClientConfig allows a custom user_agent per-instance, so it's set
        # explicitly here even though make_session() already defaults to
        # the global USER_AGENT constant.
        self._session.headers["User-Agent"] = self._config.user_agent
        self._limiter = RateLimiter(self._config.requests_per_second)

    # -- public API ------------------------------------------------

    def get_items(self) -> list[dict]:
        """Fetch the lightweight item index (slug, id, name, tradable...).

        Ordis: "Fetching the master list. All of it. Every last shiny
                Prime part."
        """
        payload = self._request("GET", "/items")
        return payload.get("data", [])

    def get_item(self, slug: str) -> dict:
        payload = self._request("GET", f"/items/{slug}")
        return payload.get("data", {})

    def get_orders_for_item(self, slug: str) -> ItemOrders:
        """Fetch current visible orders for a single item slug."""
        payload = self._request("GET", f"/orders/item/{slug}")
        raw_orders = payload.get("data", [])

        sell_orders: list[MarketOrder] = []
        buy_orders: list[MarketOrder] = []

        for raw in raw_orders:
            order = self._parse_order(raw)
            if order is None:
                continue
            if order.order_type == OrderType.SELL:
                sell_orders.append(order)
            else:
                buy_orders.append(order)

        return ItemOrders(
            slug=slug,
            sell_orders=tuple(sell_orders),
            buy_orders=tuple(buy_orders),
            fetched_at=time.time(),
        )

    # -- internal ----------------------------------------------------

    @staticmethod
    def _parse_order(raw: dict) -> Optional[MarketOrder]:
        try:
            order_type_raw = raw.get("type") or raw.get("order_type")
            platinum = raw.get("platinum")
            quantity = raw.get("quantity", 1)
            if order_type_raw is None or platinum is None:
                return None
            order_type = OrderType(str(order_type_raw).lower())
            user = raw.get("user", {}) if isinstance(raw.get("user"), dict) else {}
            status = user.get("status", "unknown")
            mod_rank_raw = raw.get("mod_rank", raw.get("modRank", raw.get("rank")))
            mod_rank = int(mod_rank_raw) if mod_rank_raw is not None else None
            return MarketOrder(
                order_type=order_type,
                platinum=float(platinum),
                quantity=int(quantity),
                user_online=status in ("ingame", "online"),
                user_status=status,
                mod_rank=mod_rank,
            )
        except (ValueError, TypeError):
            return None

    def _request(self, method: str, path: str) -> dict:
        url = f"{self._config.base_url}{path}"
        attempt = 0

        while True:
            self._limiter.wait()
            try:
                response = self._session.request(
                    method, url, timeout=self._config.timeout_seconds
                )
            except requests.RequestException as exc:
                raise MarketUnavailableError(
                    f"Ordis could not reach the market: {exc}"
                ) from exc

            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    raise MarketUnavailableError(
                        "The market responded with something that was not JSON. "
                        "Ordis is concerned."
                    ) from exc

            if response.status_code == 404:
                raise MarketNotFoundError(f"No such item on the market: {path}")

            if response.status_code == 429:
                attempt += 1
                if attempt > self._config.max_retries:
                    raise MarketRateLimitedError(
                        "Ordis got rate-limited too many times and is taking a "
                        "dignified step back."
                    )
                retry_after = response.headers.get("Retry-After")
                delay = (
                    float(retry_after)
                    if retry_after and retry_after.isdigit()
                    else self._config.backoff_base_seconds * (2 ** (attempt - 1))
                )
                time.sleep(delay)
                continue

            if 500 <= response.status_code < 600:
                attempt += 1
                if attempt > self._config.max_retries:
                    raise MarketUnavailableError(
                        f"The market returned HTTP {response.status_code} "
                        "and Ordis has given up asking, for now."
                    )
                time.sleep(self._config.backoff_base_seconds * (2 ** (attempt - 1)))
                continue

            raise MarketUnavailableError(
                f"Unexpected market response: HTTP {response.status_code}"
            )
