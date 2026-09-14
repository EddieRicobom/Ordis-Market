"""
integrations.wiki_client
=========================

Resolves an item's display name to its official Warframe Wiki URL, using
the wiki's own public MediaWiki Action API
(https://wiki.warframe.com/api.php -- documented at
https://wiki.warframe.com/w/WARFRAME_Wiki:Development_Guide).

Ordis: "The Wiki knows more about these items than I do, Operator. I find
        that mildly humbling. Only mildly."

Two lookup strategies, tried in order:

1. Exact title match via `action=query&titles=<name>&redirects=1`, which
   also transparently follows redirects -- so a renamed article (e.g. an
   old weapon name that now redirects to its current title) still
   resolves correctly.
2. If no exact page exists, a fuzzy fallback via `action=opensearch`,
   which returns the wiki's own best-guess title/URL for a near-miss
   name. This handles ambiguous or slightly-off names gracefully rather
   than simply giving up -- the result is flagged as inexact so callers
   can decide how much to trust it.

This is read-only, unauthenticated, and rate-limited to be a polite
citizen of a third-party wiki -- it never edits, logs in, or interacts
with the wiki beyond simple GET queries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

from app.common.rate_limiter import RateLimiter
from app.common.http import make_session

WIKI_API_BASE = "https://wiki.warframe.com/api.php"

# The wiki has not published a fixed numeric rate limit in its public docs
# (it varies by account/IP tier); this stays conservative and polite
# regardless, same principle as the warframe.market client.
WIKI_RATE_LIMIT_PER_SECOND = 2


class WikiClientError(Exception):
    """Base class for wiki lookup failures. Treated as a soft failure by
    callers -- a missing wiki link should never block price analysis."""


@dataclass
class WikiLookupResult:
    url: Optional[str]
    resolved_title: Optional[str]
    exact_match: bool


class WikiClient:
    def __init__(
        self,
        session: Optional[requests.Session] = None,
        requests_per_second: float = WIKI_RATE_LIMIT_PER_SECOND,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._session = session or make_session()
        self._limiter = RateLimiter(requests_per_second)
        self._timeout = timeout_seconds

    def resolve(self, name: str) -> WikiLookupResult:
        """Looks up the wiki URL for an item's display name. Never raises
        for "not found" -- only for actual request/parse failures, which
        callers should treat as "try again later", not "this item has no
        wiki page".
        """
        exact = self._exact_lookup(name)
        if exact is not None:
            return exact

        fuzzy = self._fuzzy_lookup(name)
        if fuzzy is not None:
            return fuzzy

        return WikiLookupResult(url=None, resolved_title=None, exact_match=False)

    # -- internal ------------------------------------------------------

    def _get_json(self, params: dict) -> dict:
        self._limiter.wait()
        try:
            response = self._session.get(WIKI_API_BASE, params=params, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise WikiClientError(f"Wiki lookup failed: {exc}") from exc

    def _exact_lookup(self, name: str) -> Optional[WikiLookupResult]:
        try:
            payload = self._get_json(
                {
                    "action": "query",
                    "titles": name,
                    "redirects": 1,
                    "prop": "info",
                    "inprop": "url",
                    "format": "json",
                }
            )
        except WikiClientError:
            return None

        pages = payload.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1" or "missing" in page:
                continue
            url = page.get("fullurl")
            title = page.get("title")
            if url:
                return WikiLookupResult(url=url, resolved_title=title, exact_match=True)
        return None

    def _fuzzy_lookup(self, name: str) -> Optional[WikiLookupResult]:
        try:
            payload = self._get_json(
                {
                    "action": "opensearch",
                    "search": name,
                    "limit": 1,
                    "namespace": 0,
                    "format": "json",
                }
            )
        except WikiClientError:
            return None

        # opensearch responds with [search_term, [titles], [descriptions], [urls]]
        if not isinstance(payload, list) or len(payload) < 4:
            return None
        titles, urls = payload[1], payload[3]
        if not titles or not urls:
            return None
        return WikiLookupResult(url=urls[0], resolved_title=titles[0], exact_match=False)
