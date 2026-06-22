"""Version-driven Home Assistant docs freshness.

We cannot reliably ask the LLM which version of HA docs it was trained on, so instead we
key docs freshness off the *running* HA version. A compact, hand-curated reference is
bundled (``prompts/dashboard_reference.md``). When the running instance is newer than the
baseline that reference reflects, we fetch a small curated set of upstream docs, trim them,
and cache the result under ``/data`` so it is reused until the HA version changes again.

All failures degrade to the bundled reference — docs freshness must never break generation.
"""

from __future__ import annotations

import os

import requests
from flask import current_app
from packaging.version import InvalidVersion, Version

from api.config import DATA_DIR, PROMPTS_DIR

# HA version the bundled reference reflects. If the running instance is newer (by calendar
# minor), we attempt to refresh.
DOCS_BASELINE_HA_VERSION = "2024.12"

# Where fetched references are cached (only writable inside the HA container).
DOCS_CACHE_DIR = os.path.join(DATA_DIR, "docs_cache")

# Bundled fallback reference.
_BUNDLED_REFERENCE = os.path.join(PROMPTS_DIR, "dashboard_reference.md")

# Curated, bounded upstream sources (raw markdown). Kept short on purpose to control tokens.
_DOC_SOURCES = [
    "https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_dashboards/cards.markdown",
    "https://raw.githubusercontent.com/home-assistant/home-assistant.io/current/source/_docs/automation/trigger.markdown",
]

# Hard cap on injected reference size to keep prompt token usage bounded.
_MAX_REFERENCE_CHARS = 8000

# Per-source fetch timeout (seconds).
_FETCH_TIMEOUT = 10


def _release_tuple(version: str) -> tuple[int, ...] | None:
    """Return the numeric release tuple (e.g. (2025, 6, 1)) or None if unparseable."""
    try:
        return Version(version).release
    except (InvalidVersion, TypeError):
        return None


def _is_newer_by_minor(running: str, baseline: str) -> bool:
    """True if ``running`` is newer than ``baseline`` by at least one (calendar) minor."""
    run = _release_tuple(running)
    base = _release_tuple(baseline)
    if not run or not base:
        return False
    # Compare (major, minor) only — patch releases don't change documented APIs.
    return run[:2] > base[:2]


def _read_bundled() -> str:
    try:
        with open(_BUNDLED_REFERENCE, encoding="utf-8") as f:
            return f.read()
    except OSError as exc:
        current_app.logger.warning("⚠️ Could not read bundled dashboard reference: %s", exc)
        return ""


def _cache_path(version: str) -> str:
    safe = version.replace(os.sep, "_")
    return os.path.join(DOCS_CACHE_DIR, safe, "reference.md")


def _fetch_and_cache(version: str) -> str | None:
    """Fetch curated docs for ``version``, trim, cache, and return them (or None on failure)."""
    parts: list[str] = [f"# Home Assistant Reference (fetched for {version})\n"]
    for url in _DOC_SOURCES:
        try:
            resp = requests.get(url, timeout=_FETCH_TIMEOUT)
            resp.raise_for_status()
            parts.append(resp.text)
        except Exception as exc:  # noqa: BLE001
            current_app.logger.warning("⚠️ Failed to fetch docs source %s: %s", url, exc)
            return None

    combined = "\n\n".join(parts)[:_MAX_REFERENCE_CHARS]

    try:
        path = _cache_path(version)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(combined)
        current_app.logger.info("📚 Cached refreshed HA docs for %s", version)
    except OSError as exc:
        current_app.logger.warning("⚠️ Could not cache fetched docs: %s", exc)

    return combined


def get_docs_reference(ha_version: str | None, auto_fetch: bool = True) -> str:
    """Return the active reference text for the prompt, bounded for token efficiency.

    Prefers a cached/fetched reference when the running HA version is newer than the
    bundled baseline; otherwise (and on any failure) returns the bundled reference.
    """
    bundled = _read_bundled()

    if not ha_version or not auto_fetch:
        return bundled[:_MAX_REFERENCE_CHARS]

    if not _is_newer_by_minor(ha_version, DOCS_BASELINE_HA_VERSION):
        return bundled[:_MAX_REFERENCE_CHARS]

    # Reuse a previously cached fetch for this exact version if present.
    cached_path = _cache_path(ha_version)
    try:
        if os.path.exists(cached_path):
            with open(cached_path, encoding="utf-8") as f:
                return f.read()[:_MAX_REFERENCE_CHARS]
    except OSError:
        pass

    fetched = _fetch_and_cache(ha_version)
    if fetched:
        return fetched

    current_app.logger.info("📚 Falling back to bundled HA docs reference")
    return bundled[:_MAX_REFERENCE_CHARS]
