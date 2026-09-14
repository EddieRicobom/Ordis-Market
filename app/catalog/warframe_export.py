"""
catalog.warframe_export
========================

Fetches Digital Extremes' own official "Public Export" data (also called
Mobile Export) and builds a uniqueName -> display name lookup table.

Ordis: "This is not warframe.market's data, Operator. This comes straight
        from the horse's mouth -- Digital Extremes publishes this
        specifically so companion apps, like the mobile Warframe
        Companion, can label things properly. I am simply borrowing
        their dictionary."

Why this exists
----------------
A real inventory export identifies items only by their internal Warframe
path (e.g. '/Lotus/Types/Recipes/Weapons/WeaponParts/BratonPrimeBarrel').
warframe.market's own catalog is indexed by human names and slugs, which
bear no resemblance to that path. To bridge the two, we need a
uniqueName -> human name translation table, and Digital Extremes publishes
exactly that, publicly and for free, documented at
https://wiki.warframe.com/w/Public_Export.

This is entirely read-only, static, public JSON/text data served over
plain HTTP(S) -- no game process interaction, no authentication, no
automation of any kind. It is the same data source community tools like
WFCD/warframe-items are built on.
"""

from __future__ import annotations

import lzma
from typing import Optional

import requests

from app.common.http import make_session

ORIGIN_INDEX_URL = "https://origin.warframe.com/PublicExport/index_en.txt.lzma"
CONTENT_BASE_URL = "http://content.warframe.com/PublicExport/Manifest/"

# The manifest files that can contain items an Operator might actually own.
# (Skips star chart nodes, Nightwave challenges, etc., which aren't
# inventory items.)
RELEVANT_MANIFESTS = (
    "ExportWarframes_en.json",
    "ExportWeapons_en.json",
    "ExportUpgrades_en.json",
    "ExportRecipes_en.json",
    "ExportResources_en.json",
    "ExportRelicArcane_en.json",
    "ExportGear_en.json",
    "ExportSentinels_en.json",
    "ExportFlavour_en.json",
    "ExportCustoms_en.json",
    "ExportDrones_en.json",
    "ExportSortieRewards_en.json",
)


class WarframeExportError(Exception):
    """Raised when the Public Export index/manifests can't be fetched or
    parsed. Callers should treat this as an optional enrichment step and
    fall back gracefully (e.g. to name/slug heuristics) rather than
    failing the whole catalog update over it.
    """


def parse_index(index_text: str) -> dict[str, str]:
    """Maps a manifest's base filename (e.g. 'ExportWeapons_en.json') to its
    currently content-hashed full name (e.g.
    'ExportWeapons_en.json!00_HghAEHejKwa2JJrj9gZW3g'), per the index file
    format documented at https://wiki.warframe.com/w/Public_Export.
    """
    mapping: dict[str, str] = {}
    for line in index_text.splitlines():
        line = line.strip()
        if not line or "!" not in line:
            continue
        base_name = line.split("!", 1)[0]
        mapping[base_name] = line
    return mapping


def extract_name_pairs(payload: dict) -> dict[str, str]:
    """Walks every array in a manifest's top-level JSON object and pulls
    out any {'uniqueName': ..., 'name': ...} pairs it finds, regardless of
    which category key they live under. This is deliberately schema-loose:
    the exact set of top-level keys in a manifest (e.g. 'ExportWarframes'
    vs 'ExportAbilities' within ExportWarframes_en.json) isn't something
    we depend on staying fixed across game updates.
    """
    pairs: dict[str, str] = {}
    if not isinstance(payload, dict):
        return pairs
    for value in payload.values():
        if not isinstance(value, list):
            continue
        for entry in value:
            if not isinstance(entry, dict):
                continue
            unique_name = entry.get("uniqueName")
            name = entry.get("name")
            if unique_name and name:
                pairs[unique_name] = name
    return pairs


def _decompress_index(raw_bytes: bytes) -> str:
    """Turns the Public Export index's raw response bytes into text.

    Tries, in order: standard LZMA auto-detection, the legacy
    'FORMAT_ALONE' LZMA variant explicitly (older Digital Extremes export
    tooling is documented to use this rather than the modern .xz
    container, and Python's auto-detection isn't always reliable for it),
    and finally treats the bytes as already-plain-text in case the CDN
    ever serves this uncompressed. Raises WarframeExportError with a
    diagnostic byte preview only if none of those work, so a future
    format change is easy to diagnose from a bug report instead of just
    seeing a bare 'Corrupt input data'.
    """
    try:
        return lzma.decompress(raw_bytes).decode("utf-8", errors="ignore")
    except lzma.LZMAError:
        pass

    try:
        return lzma.decompress(raw_bytes, format=lzma.FORMAT_ALONE).decode(
            "utf-8", errors="ignore"
        )
    except lzma.LZMAError:
        pass

    try:
        text = raw_bytes.decode("utf-8")
        if "!" in text and (".json" in text or ".txt" in text):
            # Looks like the expected 'name!hash' index format already
            # in plain text -- accept it rather than force a failure.
            return text
    except UnicodeDecodeError:
        pass

    preview = raw_bytes[:16].hex()
    raise WarframeExportError(
        f"Could not decompress the Public Export index as LZMA, and it "
        f"doesn't look like plain text either (first bytes: {preview}). "
        f"The export format may have changed."
    )


def fetch_unique_name_index(
    session: Optional[requests.Session] = None,
    timeout: float = 20.0,
) -> dict[str, str]:
    """Downloads and merges the relevant Public Export manifests into a
    single {uniqueName: display_name} dict.

    Raises WarframeExportError on total failure. Partial manifest failures
    (one file missing/unparseable) are skipped rather than aborting the
    whole fetch, since a partial name index is still useful.
    """
    sess = session or make_session(accept="*/*")

    try:
        index_response = sess.get(ORIGIN_INDEX_URL, timeout=timeout)
        index_response.raise_for_status()
    except (requests.RequestException, OSError) as exc:
        raise WarframeExportError(f"Could not fetch the Public Export index: {exc}") from exc

    try:
        index_text = _decompress_index(index_response.content)
    except WarframeExportError:
        raise
    except OSError as exc:
        raise WarframeExportError(
            f"Could not fetch/decompress the Public Export index: {exc}"
        ) from exc

    hashed_names = parse_index(index_text)

    merged: dict[str, str] = {}
    for base_name in RELEVANT_MANIFESTS:
        hashed = hashed_names.get(base_name)
        if not hashed:
            continue  # this manifest wasn't listed this cycle -- skip it
        url = CONTENT_BASE_URL + hashed
        try:
            response = sess.get(url, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            continue  # one bad manifest shouldn't sink the rest
        merged.update(extract_name_pairs(payload))

    if not merged:
        raise WarframeExportError("No usable data was found in any Public Export manifest.")

    return merged
