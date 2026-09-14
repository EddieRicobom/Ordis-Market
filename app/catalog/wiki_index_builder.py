"""
catalog.wiki_index_builder
============================

Builds/refreshes a WikiIndex for a given set of item names.

Ordis: "I go to the Wiki on my own time, and only when asked. This is not
        part of my regular duties. I have added it as a hobby."

This is intentionally its own separate operation, triggered only by the
Operator clicking UPDATE WIKI -- it is never called from
PortfolioAnalyzer or run as part of ANALYZE INVENTORY, so a slow or
unavailable Wiki can never slow down price/ranking calculations. The
analyzer only ever does a passive, already-cached lookup against
WikiIndex (see analysis/portfolio.py); populating that cache is this
module's job alone.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from app.catalog.wiki_index import WikiIndex
from app.integrations.wiki_client import WikiClient, WikiLookupResult


@dataclass
class WikiBuildResult:
    attempted: int
    newly_resolved: int
    newly_unresolved: int
    skipped_already_known: int
    total_known: int = 0
    """Total distinct names the WikiIndex knows about after this run
    (resolved + confirmed-unresolved), for status displays that want the
    cumulative total rather than just this run's delta."""


class WikiIndexBuilder:
    def __init__(self, wiki_index: WikiIndex, client: WikiClient, max_workers: int = 3) -> None:
        self._index = wiki_index
        self._client = client
        self._max_workers = max(1, max_workers)
        """Bounded concurrency for the actual Wiki network calls. The
        WikiClient's own RateLimiter is thread-safe and still caps real
        request throughput regardless of how many threads call it, so
        this only overlaps request latency with that limit's idle time --
        it cannot exceed the rate limit or make things slower than
        sequential in the worst case. Index writes themselves
        (set_resolved/set_unresolved) happen back on the calling thread
        after each fetch completes, not from worker threads, so WikiIndex
        itself never needs its own locking."""

    def build_for_names(
        self,
        names: Iterable[str],
        force: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> WikiBuildResult:
        """Resolves a wiki URL for each unique, non-empty name given.

        By default, names already attempted (resolved or previously found
        to have no page) are skipped -- pass force=True to re-check them
        (e.g. after the Wiki reorganizes something). Handles missing,
        renamed, and ambiguous items gracefully: a name with no page is
        recorded as such (not retried every time) rather than treated as
        an error, and WikiClient itself already resolves renames via
        redirects and near-misses via its fuzzy fallback.
        """
        unique_names = sorted({n.strip() for n in names if n and n.strip()})
        total = len(unique_names)

        newly_resolved = 0
        newly_unresolved = 0
        skipped = 0
        completed = 0

        def _tick() -> None:
            nonlocal completed
            completed += 1
            if progress_callback:
                progress_callback(completed, total)

        names_to_fetch = []
        for name in unique_names:
            if not force and self._index.has_been_attempted(name):
                skipped += 1
                _tick()
            else:
                names_to_fetch.append(name)

        def _resolve(name: str) -> tuple[str, WikiLookupResult]:
            try:
                return name, self._client.resolve(name)
            except Exception:  # noqa: BLE001 - one bad name must not sink the batch
                return name, WikiLookupResult(url=None, resolved_title=None, exact_match=False)

        if names_to_fetch:
            worker_count = min(self._max_workers, len(names_to_fetch))
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = [executor.submit(_resolve, name) for name in names_to_fetch]
                for future in as_completed(futures):
                    name, result = future.result()
                    if result.url:
                        self._index.set_resolved(name, result.url)
                        newly_resolved += 1
                    else:
                        self._index.set_unresolved(name)
                        newly_unresolved += 1
                    _tick()

        self._index.save()

        return WikiBuildResult(
            attempted=total - skipped,
            newly_resolved=newly_resolved,
            newly_unresolved=newly_unresolved,
            skipped_already_known=skipped,
            total_known=len(self._index),
        )
