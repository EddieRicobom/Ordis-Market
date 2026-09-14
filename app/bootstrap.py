"""
bootstrap
=========

Checks that Ordis Market's runtime dependencies are installed, and installs
whatever is missing via pip before the rest of the app tries to import them.

Ordis: "Before we begin, allow me to make sure all my parts are attached.
        I would hate to start a sentence and discover halfway through that
        I am missing a module."

This module is intentionally dependency-free itself (only stdlib: importlib,
subprocess, sys) so it can safely run *before* anything that needs PySide6,
requests, or openpyxl is imported.
"""

from __future__ import annotations

import importlib
import re
import subprocess
import sys
from dataclasses import dataclass
from importlib import metadata
from typing import Mapping, Optional


# module import name -> pip requirement spec
DEFAULT_REQUIREMENTS: Mapping[str, str] = {
    "PySide6": "PySide6>=6.7,<7.0",
    "requests": "requests>=2.31,<3.0",
    "openpyxl": "openpyxl>=3.1,<4.0",
}


@dataclass
class BootstrapResult:
    already_satisfied: tuple[str, ...]
    installed: tuple[str, ...]
    failed: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failed


def _parse_min_version(spec: str) -> Optional[tuple[int, ...]]:
    """Extracts the '>=X.Y' minimum version bound from a pip requirement
    spec like 'PySide6>=6.7,<7.0', returning (6, 7). Returns None if the
    spec has no such bound (nothing to enforce beyond "is it installed")."""
    match = re.search(r">=\s*([0-9]+(?:\.[0-9]+)*)", spec)
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def _installed_version(module_name: str) -> Optional[tuple[int, ...]]:
    """The installed distribution's version as a tuple of ints, or None
    if it can't be determined (not installed via pip metadata, or a
    version string we don't know how to parse) -- treated as "unknown",
    not "definitely fine" or "definitely needs reinstalling"."""
    try:
        raw = metadata.version(module_name)
    except metadata.PackageNotFoundError:
        return None
    match = re.match(r"([0-9]+(?:\.[0-9]+)*)", raw)
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def _is_unsatisfied(module_name: str, spec: str) -> bool:
    """True if the module can't be imported at all, OR is importable but
    below the spec's minimum version.

    That second case is the real gap an import-only check misses: if a
    future Ordis Market release bumps a minimum dependency version, an
    already-installed *older* version would import just fine and never
    get upgraded automatically, silently leaving the Operator on a stale
    dependency. Checking the installed version, not just presence,
    closes that gap.
    """
    try:
        importlib.import_module(module_name)
    except ImportError:
        return True

    min_version = _parse_min_version(spec)
    if min_version is None:
        return False

    installed = _installed_version(module_name)
    if installed is None:
        return False  # can't tell -- don't force a reinstall on a guess

    return installed < min_version


def _find_missing(requirements: Mapping[str, str]) -> list[str]:
    return [name for name, spec in requirements.items() if _is_unsatisfied(name, spec)]


def ensure_dependencies(
    requirements: Mapping[str, str] = DEFAULT_REQUIREMENTS,
    auto_install: bool = True,
    quiet: bool = False,
) -> BootstrapResult:
    """Verifies each required module can be imported; installs any that
    cannot be found via `pip install`, then re-checks.

    Returns a BootstrapResult describing what was already fine, what got
    installed, and what (if anything) still failed. Never raises on its
    own -- callers decide what to do with a failed result.
    """
    missing = _find_missing(requirements)
    already_satisfied = tuple(m for m in requirements if m not in missing)

    if not missing:
        return BootstrapResult(already_satisfied=already_satisfied, installed=(), failed=())

    if not auto_install:
        return BootstrapResult(
            already_satisfied=already_satisfied, installed=(), failed=tuple(missing)
        )

    specs = [requirements[m] for m in missing]
    if not quiet:
        print(f"[Ordis Market] Installing missing dependencies: {', '.join(specs)}")
        print("[Ordis Market] This only happens once. Ordis dislikes repeating himself.")

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", *specs],
            check=True,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        if not quiet:
            print(f"[Ordis Market] Automatic installation failed: {exc}")
        return BootstrapResult(
            already_satisfied=already_satisfied, installed=(), failed=tuple(missing)
        )

    # Re-check: pip succeeding doesn't always guarantee the interpreter's
    # import cache reflects it, so verify for real before declaring victory.
    importlib.invalidate_caches()
    still_missing = _find_missing({m: requirements[m] for m in missing})
    installed = tuple(m for m in missing if m not in still_missing)

    return BootstrapResult(
        already_satisfied=already_satisfied,
        installed=installed,
        failed=tuple(still_missing),
    )
