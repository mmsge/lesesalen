"""Bibliographic data and cover images.

A book edition is not anyone's personal information, so unlike post enrichment
this *is* persisted — once, shared by every reader who sees the book.

Covers are downloaded here, at cache time, and served from our own origin. That
is a privacy property as much as a performance one: readers never hit BookWyrm
instances for images, so no reader's IP leaks outward, and because the fetch
happens when the book is first cached rather than per view, this server learns
nothing about who looked at what.

It is also an XSS boundary (§9.4). A cover is a file from a remote instance that
we then serve same-origin, so a malicious SVG would execute as our own script.
Raster formats only, re-encoded on ingest, never stored or served as uploaded.

Enrichment fallback chain, in order: the ActivityPub object, then Open Graph
tags on the book page, then Open Library by ISBN, then by title and author, then
nothing — and a text-only card, which always beats a missing one.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import re
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote, urljoin, urlsplit

from PIL import Image

from . import blurhash, config, db, instances, netfetch, robots, sanitise
from .cache import TTLCache

# Guard against decompression bombs before Pillow ever decodes a remote file.
Image.MAX_IMAGE_PIXELS = 40_000_000

AP_ACCEPT = 'application/activity+json, application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
RASTER_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/jpg"}
RASTER_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}

_BOOK_TTL = 30 * 24 * 3600
_author_names: TTLCache[str] = TTLCache(max_size=2000, ttl=24 * 3600)
_book_locks: dict[str, asyncio.Lock] = {}


def book_id(ap_url: str) -> str:
    return hashlib.sha256(ap_url.encode("utf-8")).hexdigest()[:20]


def _lock(key: str) -> asyncio.Lock:
    lock = _book_locks.get(key)
    if lock is None:
        lock = _book_locks[key] = asyncio.Lock()
    return lock


# ── Open Graph scraping ──────────────────────────────────────────────────────

class _OpenGraph(HTMLParser):
    """Pull og:*/twitter:* meta out of a page, ignoring everything else.

    A stdlib parser rather than a DOM library: we only ever read attributes of
    <meta> elements and never render any of this, and the values go through the
    sanitiser before they reach a client.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        data = {k.lower(): (v or "") for k, v in attrs}
        key = data.get("property") or data.get("name")
        content = data.get("content")
        if key and content and key.lower().startswith(("og:", "twitter:", "book:")):
            self.tags.setdefault(key.lower(), content)


# ── parsing an ActivityPub Edition ───────────────────────────────────────────

def _first_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list):
        for item in value:
            found = _first_str(item)
            if found:
                return found
    if isinstance(value, dict):
        for key in ("name", "value", "content", "@value", "href", "url", "id"):
            found = _first_str(value.get(key))
            if found:
                return found
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 < value < 100_000 else None
    if isinstance(value, str):
        digits = re.sub(r"[^0-9]", "", value)
        if digits:
            try:
                number = int(digits)
            except ValueError:
                return None
            return number if 0 < number < 100_000 else None
    return None


def _isbn(document: dict[str, Any]) -> str | None:
    for key in ("isbn13", "isbn10", "isbn"):
        raw = _first_str(document.get(key))
        if raw:
            cleaned = re.sub(r"[^0-9Xx]", "", raw).upper()
            if len(cleaned) in (10, 13):
                return cleaned
    return None


def _cover_url(document: dict[str, Any], base: str) -> str | None:
    cover = document.get("cover")
    candidate = None
    if isinstance(cover, dict):
        candidate = _first_str(cover.get("url")) or _first_str(cover.get("href"))
    elif isinstance(cover, str):
        candidate = cover
    if not candidate:
        candidate = _first_str(document.get("image"))
    if not candidate:
        return None
    return urljoin(base, candidate)


async def _author_name(url: str, host: str) -> str | None:
    cached = _author_names.get(url)
    if cached:
        return cached
    try:
        fetched = await netfetch.fetch(
            url, allowed_hosts={host}, accept=AP_ACCEPT, max_bytes=config.MAX_JSON_BYTES
        )
        document = json.loads(fetched.body.decode("utf-8", "replace"))
    except (netfetch.FetchError, ValueError):
        return None
    if not isinstance(document, dict):
        return None
    name = sanitise.clean_text(_first_str(document.get("name")), limit=200)
    if name:
        _author_names.put(url, name)
    return name or None


async def _authors(document: dict[str, Any], host: str) -> list[str]:
    raw = document.get("authors") or document.get("author") or []
    if isinstance(raw, (str, dict)):
        raw = [raw]
    names: list[str] = []
    urls: list[str] = []
    for entry in raw[:6]:  # a cap, so one book can't fan out into a dozen fetches
        if isinstance(entry, dict) and _first_str(entry.get("name")):
            names.append(sanitise.clean_text(_first_str(entry.get("name")), limit=200))
        elif isinstance(entry, str) and entry.startswith("https://"):
            urls.append(entry)
        elif isinstance(entry, str):
            names.append(sanitise.clean_text(entry, limit=200))
    if urls:
        resolved = await asyncio.gather(
            *(_author_name(url, host) for url in urls), return_exceptions=True
        )
        names.extend(
            name for name in resolved if isinstance(name, str) and name
        )
    return [name for name in names if name][:6]


# ── covers ───────────────────────────────────────────────────────────────────

async def _store_cover(identifier: str, url: str, host: str) -> tuple[str, str] | None:
    """Download, validate, re-encode. Returns (filename, blurhash) or None.

    The cover host is taken from the URL itself rather than from the instance
    allowlist, and that is a deliberate, bounded exception. BookWyrm keeps cover
    files on object storage, not on the instance domain — bookwyrm.social serves
    them from `bookwyrm-social.sfo3.digitaloceanspaces.com` — so requiring the
    instance's own host here would mean no covers at all, anywhere.

    What makes it safe enough: this URL is not caller-supplied. It comes out of
    an ActivityPub document we already fetched from a nodeinfo-confirmed
    BookWyrm instance, so the allowlist has done its job one step earlier. Every
    other guard still applies in full — https only, public addresses only,
    redirect re-validation, size cap, raster-only, and a full re-encode.
    """
    cover_host = netfetch.normalise_domain(urlsplit(url).hostname or "")
    if not cover_host:
        return None
    try:
        fetched = await netfetch.fetch(
            url,
            allowed_hosts={cover_host, host} | config.FALLBACK_HOSTS,
            accept="image/jpeg, image/png, image/webp, image/gif",
            max_bytes=config.MAX_IMAGE_BYTES,
        )
    except netfetch.FetchError:
        return None

    declared = fetched.content_type.split(";")[0].strip().lower()
    # SVG is the whole point of this check: served from our origin it would be
    # same-origin script. Reject on the declared type *and* on the decoded
    # format below, because a declared type is just a claim.
    if declared and declared not in RASTER_TYPES:
        return None

    try:
        with Image.open(io.BytesIO(fetched.body)) as image:
            if image.format not in RASTER_FORMATS:
                return None
            image.load()
            rgb = image.convert("RGB")
            rgb.thumbnail((config.COVER_MAX_EDGE, config.COVER_MAX_EDGE))
            hashed = blurhash.encode_image(rgb)
            buffer = io.BytesIO()
            # Re-encoded from decoded pixels, so nothing of the original file —
            # metadata, trailing payloads, colour-profile exploits — survives.
            rgb.save(buffer, format="JPEG", quality=config.COVER_QUALITY, optimize=True)
    except (OSError, ValueError, Image.DecompressionBombError):
        return None

    filename = f"{identifier}.jpg"
    config.COVER_DIR.mkdir(parents=True, exist_ok=True)
    temporary = config.COVER_DIR / f".{filename}.tmp"
    temporary.write_bytes(buffer.getvalue())
    temporary.replace(config.COVER_DIR / filename)
    return filename, hashed


# ── the fallback chain ───────────────────────────────────────────────────────

async def _from_activitypub(ap_url: str, host: str) -> dict[str, Any] | None:
    try:
        fetched = await netfetch.fetch(
            ap_url, allowed_hosts={host}, accept=AP_ACCEPT, max_bytes=config.MAX_JSON_BYTES
        )
        document = json.loads(fetched.body.decode("utf-8", "replace"))
    except (netfetch.FetchError, ValueError):
        return None
    if not isinstance(document, dict):
        return None
    title = sanitise.clean_text(_first_str(document.get("title")) or _first_str(document.get("name")), limit=400)
    if not title:
        return None
    return {
        "title": title,
        "subtitle": sanitise.clean_text(document.get("subtitle"), limit=400) or None,
        "authors": await _authors(document, host),
        "pages": _as_int(document.get("pages")),
        "isbn": _isbn(document),
        "description": sanitise.clean_text(document.get("description"), limit=1200) or None,
        "bookwyrm_url": _first_str(document.get("id")) or ap_url,
        "_cover_url": _cover_url(document, ap_url),
    }


async def _from_open_graph(ap_url: str, host: str) -> dict[str, Any] | None:
    if not await robots.may_scrape(ap_url):
        return None
    try:
        fetched = await netfetch.fetch(
            ap_url,
            allowed_hosts={host},
            accept="text/html",
            max_bytes=config.MAX_HTML_BYTES,
        )
    except netfetch.FetchError:
        return None
    parser = _OpenGraph()
    try:
        parser.feed(fetched.body.decode("utf-8", "replace"))
    except (ValueError, AssertionError):
        return None
    tags = parser.tags
    title = sanitise.clean_text(tags.get("og:title") or tags.get("twitter:title"), limit=400)
    if not title:
        return None
    image = tags.get("og:image") or tags.get("twitter:image")
    return {
        "title": title,
        "subtitle": None,
        "authors": [],
        "pages": None,
        "isbn": None,
        "description": sanitise.clean_text(
            tags.get("og:description") or tags.get("twitter:description"), limit=1200
        ) or None,
        "bookwyrm_url": ap_url,
        "_cover_url": urljoin(ap_url, image) if image else None,
    }


async def _open_library(query_url: str) -> dict[str, Any] | None:
    try:
        fetched = await netfetch.fetch(
            query_url,
            allowed_hosts=config.FALLBACK_HOSTS,
            accept="application/json",
            max_bytes=config.MAX_JSON_BYTES,
        )
        document = json.loads(fetched.body.decode("utf-8", "replace"))
    except (netfetch.FetchError, ValueError):
        return None
    docs = document.get("docs") if isinstance(document, dict) else None
    if not docs:
        return None
    entry = docs[0]
    if not isinstance(entry, dict):
        return None
    title = sanitise.clean_text(entry.get("title"), limit=400)
    if not title:
        return None
    authors = [
        sanitise.clean_text(name, limit=200)
        for name in (entry.get("author_name") or [])[:6]
        if isinstance(name, str)
    ]
    cover = entry.get("cover_i")
    return {
        "title": title,
        "subtitle": sanitise.clean_text(entry.get("subtitle"), limit=400) or None,
        "authors": [a for a in authors if a],
        "pages": _as_int(entry.get("number_of_pages_median")),
        "isbn": None,
        "description": None,
        "bookwyrm_url": None,
        "_cover_url": (
            f"https://covers.openlibrary.org/b/id/{int(cover)}-L.jpg"
            if isinstance(cover, int)
            else None
        ),
    }


async def _from_open_library(isbn: str | None, title: str | None, author: str | None):
    if isbn:
        found = await _open_library(
            f"https://openlibrary.org/search.json?isbn={quote(isbn)}&limit=1"
        )
        if found:
            found["isbn"] = isbn
            return found
    if title:
        query = f"https://openlibrary.org/search.json?title={quote(title)}&limit=1"
        if author:
            query += f"&author={quote(author)}"
        return await _open_library(query)
    return None


# ── the entry point ──────────────────────────────────────────────────────────

async def ensure_book(ap_url: str) -> dict[str, Any] | None:
    """Return the cached book for `ap_url`, fetching it the first time.

    Returns None when the URL is not on a confirmed BookWyrm host — the same
    allowlist gate as everything else in this service.
    """
    host = netfetch.normalise_domain(urlsplit(ap_url).hostname or "")
    if not host or not instances.is_confirmed_bookwyrm(host):
        return None

    identifier = book_id(ap_url)
    cached = db.get_book(identifier)
    if cached and (time.time() - cached["fetched_at"]) < _BOOK_TTL:
        return cached

    async with _lock(identifier):
        # Another request may have filled it while we waited for the lock.
        cached = db.get_book(identifier)
        if cached and (time.time() - cached["fetched_at"]) < _BOOK_TTL:
            return cached

        parsed = await _from_activitypub(ap_url, host)
        if parsed is None:
            parsed = await _from_open_graph(ap_url, host)
        if parsed is None:
            parsed = await _from_open_library(None, None, None)
        if parsed is None:
            # Nothing worked. Record the miss so we don't hammer the origin on
            # every render; the client falls back to a text-only card.
            record = {
                "id": identifier,
                "ap_url": ap_url,
                "title": None,
                "subtitle": None,
                "authors": [],
                "pages": None,
                "isbn": None,
                "description": None,
                "bookwyrm_url": ap_url,
                "cover_file": None,
                "blurhash": None,
            }
            db.put_book(record)
            return db.get_book(identifier)

        # Top up thin results from Open Library rather than replacing them.
        if not parsed.get("authors") or not parsed.get("pages"):
            supplement = await _from_open_library(
                parsed.get("isbn"),
                parsed.get("title"),
                (parsed.get("authors") or [None])[0],
            )
            if supplement:
                for key in ("authors", "pages", "description"):
                    if not parsed.get(key) and supplement.get(key):
                        parsed[key] = supplement[key]
                if not parsed.get("_cover_url") and supplement.get("_cover_url"):
                    parsed["_cover_url"] = supplement["_cover_url"]

        cover_file = cached["cover_file"] if cached else None
        cover_hash = cached["blurhash"] if cached else None
        if parsed.get("_cover_url") and not cover_file:
            stored = await _store_cover(identifier, parsed["_cover_url"], host)
            if stored:
                cover_file, cover_hash = stored

        record = {
            "id": identifier,
            "ap_url": ap_url,
            "title": parsed.get("title"),
            "subtitle": parsed.get("subtitle"),
            "authors": parsed.get("authors") or [],
            "pages": parsed.get("pages"),
            "isbn": parsed.get("isbn"),
            "description": parsed.get("description"),
            "bookwyrm_url": parsed.get("bookwyrm_url") or ap_url,
            "cover_file": cover_file,
            "blurhash": cover_hash,
        }
        db.put_book(record)
        return db.get_book(identifier)


def public_book(record: dict[str, Any]) -> dict[str, Any]:
    """The shape the client sees. Nynorsk keys, no internal paths."""
    return {
        "id": record["id"],
        "tittel": record["title"],
        "undertittel": record["subtitle"],
        "forfattarar": record["authors"],
        "sider": record["pages"],
        "isbn": record["isbn"],
        "omtale": record["description"],
        "bookwyrm_url": record["bookwyrm_url"],
        "omslag": f"/omslag/{record['id']}" if record["cover_file"] else None,
        "blurhash": record["blurhash"],
    }
