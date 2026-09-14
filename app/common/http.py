"""
common.http
============

Shared HTTP session helper so every client in this project (warframe.market,
the Warframe Wiki) identifies itself consistently and doesn't duplicate the
same few lines of session/header setup.

Ordis: "I introduce myself the same way everywhere I go. It's only polite."
"""

from __future__ import annotations

from typing import Optional

import requests

from app.config.settings import USER_AGENT


def make_session(accept: str = "application/json", extra_headers: Optional[dict] = None) -> requests.Session:
    session = requests.Session()
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if extra_headers:
        headers.update(extra_headers)
    session.headers.update(headers)
    return session
