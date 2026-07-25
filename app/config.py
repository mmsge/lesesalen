"""Configuration. Every value has a working default — lesesalen needs no .env."""
from __future__ import annotations

import os
import pathlib

from . import __version__


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


DATA_DIR = pathlib.Path(os.environ.get("LESESALEN_DATA_DIR", "./data")).resolve()
COVER_DIR = DATA_DIR / "covers"
DB_PATH = DATA_DIR / "lesesalen.db"

BASE_URL = os.environ.get("LESESALEN_BASE_URL", "https://lesesalen.msge.no").rstrip("/")

# Identify ourselves honestly to the instances we fetch from, with a page a
# curious admin can read (§7 of the brief: politeness to origin instances).
USER_AGENT = f"Lesesalen/{__version__} (+{BASE_URL}/om)"

# Enrichment cache — in memory, never on disk. A restart empties it, which is
# correct: the cache exists to spare BookWyrm instances repeat fetches, not to
# accumulate a corpus (ADR 0005).
ENRICH_CACHE_SIZE = _env_int("LESESALEN_ENRICH_CACHE_SIZE", 2000)
ENRICH_CACHE_TTL = _env_int("LESESALEN_ENRICH_CACHE_TTL", 3600)

# Actor documents, for the outbox walk: which URL is an actor's outbox, and how
# many items it holds. Also memory-only, and longer-lived than an enrichment
# because an outbox URL essentially never moves — but still volatile, because the
# keys are the actor URIs of accounts somebody follows (ADR 0003).
ACTOR_CACHE_SIZE = _env_int("LESESALEN_ACTOR_CACHE_SIZE", 500)
ACTOR_CACHE_TTL = _env_int("LESESALEN_ACTOR_CACHE_TTL", 6 * 3600)

# A nodeinfo answer is infrastructure metadata and changes rarely: 30 days.
INSTANCE_TTL = _env_int("LESESALEN_INSTANCE_TTL", 30 * 24 * 3600)
# Don't re-probe a dead or non-BookWyrm host on every request either.
INSTANCE_NEGATIVE_TTL = _env_int("LESESALEN_INSTANCE_NEGATIVE_TTL", 24 * 3600)

# Per-IP token bucket on the API.
RATE_PER_SEC = _env_float("LESESALEN_RATE_PER_SEC", 2.0)
RATE_BURST = _env_int("LESESALEN_RATE_BURST", 40)

# Politeness: minimum seconds between requests to any one origin domain.
DOMAIN_INTERVAL = _env_float("LESESALEN_DOMAIN_INTERVAL", 1.0)

# Outbound limits. Small on purpose — an AP object is a few kB.
FETCH_TIMEOUT = _env_float("LESESALEN_FETCH_TIMEOUT", 10.0)
MAX_JSON_BYTES = _env_int("LESESALEN_MAX_JSON_BYTES", 512 * 1024)
MAX_HTML_BYTES = _env_int("LESESALEN_MAX_HTML_BYTES", 1024 * 1024)
MAX_IMAGE_BYTES = _env_int("LESESALEN_MAX_IMAGE_BYTES", 4 * 1024 * 1024)
MAX_REDIRECTS = _env_int("LESESALEN_MAX_REDIRECTS", 3)

# Request-shape caps, so one caller can't turn a batch endpoint into a fan-out.
MAX_DOMAINS_PER_REQUEST = _env_int("LESESALEN_MAX_DOMAINS_PER_REQUEST", 100)
MAX_URIS_PER_REQUEST = _env_int("LESESALEN_MAX_URIS_PER_REQUEST", 40)
# How many origin fetches one /api/berik call may trigger. Cache hits are free.
ENRICH_CONCURRENCY = _env_int("LESESALEN_ENRICH_CONCURRENCY", 4)

# Outbox walking. The page number is an integer we build a URL from, so it has to
# be bounded: without a cap, `side: 100000` is a request to walk somebody's whole
# history in one go. 400 pages is ~6000 posts, deeper than any real shelf.
MAX_OUTBOX_PAGE = _env_int("LESESALEN_MAX_OUTBOX_PAGE", 400)
# BookWyrm serves 15 per page. The cap is for a hostile or broken origin that
# answers with thousands, each of which would cost a book lookup.
MAX_OUTBOX_ITEMS = _env_int("LESESALEN_MAX_OUTBOX_ITEMS", 60)

# Covers are re-encoded on ingest (§9.4) — never stored or served as uploaded.
COVER_MAX_EDGE = _env_int("LESESALEN_COVER_MAX_EDGE", 800)
COVER_QUALITY = _env_int("LESESALEN_COVER_QUALITY", 82)

# LOCAL TESTING ONLY. With this on, /api/berik will happily fetch 127.0.0.1 and
# 169.254.169.254 — i.e. it becomes an SSRF hole into the box (ADR 0003).
ALLOW_PRIVATE_ADDRESSES = _env_bool("LESESALEN_ALLOW_PRIVATE_ADDRESSES", False)

# Non-BookWyrm hosts the enrichment fallback chain is allowed to reach. Kept
# tiny and explicit: everything else must be nodeinfo-confirmed BookWyrm first.
FALLBACK_HOSTS = frozenset({"openlibrary.org", "covers.openlibrary.org"})
