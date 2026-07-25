"""The whole point of the server: recovering what Mastodon threw away.

A BookWyrm review reaches a Mastodon home timeline as a Status with `content`
HTML and nothing else. The rating, the review title, the quoted passage, the
page position and the link to the book are custom ActivityPub properties
Mastodon has no column for, so they are simply gone by the time the browser
sees the post.

The origin object is still public and addressable, though, and its URI even
encodes its own type:

    https://bookwyrm.social/user/mvrkws/generatednote/12091719   reading status
    https://bookwyrm.social/user/mvrkws/comment/11996174         comment
    https://bookwyrm.social/user/mvrkws/review/…                 review
    https://bookwyrm.social/user/mvrkws/quotation/…              quotation

Fetching it with `Accept: application/activity+json` returns the full object.
The browser cannot do this because BookWyrm instances send no CORS headers for
ActivityPub fetches — that single fact is the entire reason this process exists.

Results live in an in-memory TTL cache and are never written to disk (ADR 0005),
and no URI passing through here is ever logged (ADR 0003).
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from urllib.parse import urlsplit

from . import books, config, db, instances, netfetch, sanitise
from .cache import TTLCache

# A post that is not a book post is the common case, so negative results are
# cached too — re-fetching them on every scroll would be rude to the origin.
# `NOT_A_BOOK_POST` is that negative, stored in the same cache so it expires on
# the same TTL and leaves the process the same way: with the process.
NOT_A_BOOK_POST = object()

_cache: TTLCache[Any] = TTLCache(
    max_size=config.ENRICH_CACHE_SIZE, ttl=config.ENRICH_CACHE_TTL
)
_semaphore = asyncio.Semaphore(config.ENRICH_CONCURRENCY)

KIND_REVIEW = "omtale"
KIND_RATING = "vurdering"
KIND_COMMENT = "kommentar"
KIND_QUOTATION = "sitat"
KIND_READING_STATUS = "lesestatus"

_TYPE_TO_KIND = {
    "review": KIND_REVIEW,
    "rating": KIND_RATING,
    "reviewrating": KIND_RATING,
    "comment": KIND_COMMENT,
    "quotation": KIND_QUOTATION,
    "generatednote": KIND_READING_STATUS,
}

# The URL path segment is the primary type discriminator, and this is not a
# shortcut — it is the only thing that works.
#
# BookWyrm serves two representations of a status. Its own kind gets the rich
# one (`type: "Review"`, with `rating`, `name` and `quote`); everybody else gets
# the "pure" one, where the type collapses to `Note` and the rich fields are
# folded into the rendered `content`. An unauthenticated third-party fetch —
# which is all we ever do — gets the pure form, verified against
# bookwyrm.social: a comment and a reading status both come back as `Note`.
#
# But the URI still says what the object is:
#   /user/x/review/1        /user/x/quotation/2      /user/x/generatednote/3
#
# So we read the segment first and treat the `type` field as a refinement for
# the instances that do serve the rich form. Do not "simplify" this to trust
# `type` — it will classify every post on bookwyrm.social as a plain note.
# See ADR 0007.
_SEGMENT_TO_KIND = {
    "review": KIND_REVIEW,
    "rating": KIND_RATING,
    "comment": KIND_COMMENT,
    "quotation": KIND_QUOTATION,
    "generatednote": KIND_READING_STATUS,
}

# BookWyrm's own machine-readable shelf state, present on the pure Note.
_READING_STATUS_FIELD = {
    "to-read": "vil-lesa",
    "reading": "byrja",
    "read": "ferdig",
    "stopped-reading": "slutta",
}

# Fallback for reading statuses, whose GeneratedNote carries no `readingStatus`
# field — the state is only in the generated prose. Fragile by nature: a
# BookWyrm copy change or a non-English locale lands us on the generic
# "lesestatus" card, which is a deliberately survivable outcome rather than a
# broken one.
_STATUS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("vil-lesa", re.compile(r"\bwants? to read\b|\bvil (?:lesa|lese)\b|\bwill read\b", re.I)),
    ("ferdig", re.compile(r"\bfinished reading\b|\bhas read\b|\bferdig med\b|\bles(?:te)? ferdig\b", re.I)),
    ("slutta", re.compile(r"\bstopped reading\b|\bgave up on\b|\bslutta (?:å lesa|med)\b", re.I)),
    ("byrja", re.compile(r"\bstarted reading\b|\bis reading\b|\bbyrja (?:å lesa|på)\b|\bbegan reading\b", re.I)),
]

# In the pure representation a review's title becomes
# `Review of "The Book" (4 stars): the actual title`, which is the only place
# the rating survives. Recover both.
_PURE_REVIEW_NAME = re.compile(
    r"^review of\s+\"(?P<book>.*)\"\s*(?:\((?P<rating>[\d.]+)\s*stars?\))?\s*:\s*(?P<title>.*)$",
    re.I | re.S,
)

_TAG_BOOK_TYPES = {"edition", "book", "work"}

# Any link to an edition on the same host, for objects that carry neither
# `inReplyToBook` nor an Edition tag.
_BOOK_HREF = re.compile(r'href="(https://[^"]+/book/\d+)"')


def _text_of(html: str) -> str:
    return sanitise.clean_text(html, limit=600)


def _reading_state(content_html: str) -> str | None:
    text = _text_of(content_html)
    for state, pattern in _STATUS_PATTERNS:
        if pattern.search(text):
            return state
    return None


def _rating(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if not 0 <= number <= 5:
        return None
    return round(number * 2) / 2  # BookWyrm allows halves; anything else is noise


def _position(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = int(value)
    elif isinstance(value, str) and value.strip().isdigit():
        number = int(value.strip())
    else:
        return None
    return number if 0 <= number <= 100_000 else None


def _position_mode(value: Any) -> str:
    if isinstance(value, str) and value.strip().lower() in {"pct", "percent", "prosent"}:
        return "prosent"
    return "side"


def _book_url(document: dict[str, Any], host: str) -> str | None:
    """Find the edition this post is about.

    Reviews, comments and quotations carry `inReplyToBook`. Generated notes do
    not — the books they mention are serialised as `tag` entries of type
    Edition, so both shapes have to be handled.
    """
    direct = document.get("inReplyToBook")
    if isinstance(direct, str) and direct.startswith("https://"):
        return direct
    if isinstance(direct, dict):
        candidate = direct.get("id") or direct.get("href")
        if isinstance(candidate, str) and candidate.startswith("https://"):
            return candidate

    tags = document.get("tag")
    if isinstance(tags, dict):
        tags = [tags]
    for tag in tags or []:
        if not isinstance(tag, dict):
            continue
        kind = str(tag.get("type") or "").lower()
        if kind in _TAG_BOOK_TYPES:
            candidate = tag.get("href") or tag.get("id")
            if isinstance(candidate, str) and candidate.startswith("https://"):
                if netfetch.normalise_domain(urlsplit(candidate).hostname or "") == host:
                    return candidate

    # Last resort: a reading status links the edition from its prose and carries
    # neither `inReplyToBook` nor an Edition tag.
    content = document.get("content")
    if isinstance(content, str):
        for match in _BOOK_HREF.finditer(content):
            candidate = match.group(1)
            if netfetch.normalise_domain(urlsplit(candidate).hostname or "") == host:
                return candidate
    return None


def kind_from_uri(uri: str) -> str | None:
    """The object kind, read off the URI path — see the note on _SEGMENT_TO_KIND."""
    parts = [part for part in urlsplit(uri).path.split("/") if part]
    for segment in reversed(parts):
        found = _SEGMENT_TO_KIND.get(segment.lower())
        if found:
            return found
    return None


def parse_object(document: dict[str, Any], host: str, uri: str = "") -> dict[str, Any] | None:
    """Turn a BookWyrm ActivityPub object into the shape the client renders.

    Handles both representations: the rich one (`type: "Review"` with `rating`,
    `name`, `quote`) that BookWyrm serves its own kind, and the pure one
    (everything collapsed to a `Note`) that third parties like us actually get.
    """
    if not isinstance(document, dict):
        return None

    identifier = document.get("id") if isinstance(document.get("id"), str) else None
    raw_type = str(document.get("type") or "").strip().lower()
    # URI first, `type` as a refinement — see the note on _SEGMENT_TO_KIND.
    kind = kind_from_uri(uri or identifier or "") or _TYPE_TO_KIND.get(raw_type)

    content_html = sanitise.clean_html(document.get("content"))
    rating = _rating(document.get("rating"))
    quote_html = sanitise.clean_html(document.get("quote"))
    title = sanitise.clean_text(document.get("name"), limit=300)
    book_url = _book_url(document, host)

    if kind is None:
        # A plain Note that replies to a book is a comment in all but name.
        if raw_type in {"note", "article"} and book_url:
            kind = KIND_COMMENT
        else:
            return None

    # Pure representation: the rating and the real title only survive inside
    # `name`, as `Review of "The Book" (4 stars): the actual title`.
    if title and (rating is None or _PURE_REVIEW_NAME.match(title)):
        match = _PURE_REVIEW_NAME.match(title)
        if match:
            if rating is None:
                rating = _rating(match.group("rating"))
            title = sanitise.clean_text(match.group("title"), limit=300)

    # Pure representation of a quotation: the passage is rendered into `content`
    # rather than carried in `quote`. The card needs something to set large.
    if kind == KIND_QUOTATION and not quote_html:
        quote_html = content_html
        content_html = ""

    # A "review" with a rating and no prose is a library slip, not an essay —
    # the two want completely different cards, so classify on the content.
    if kind == KIND_REVIEW and rating is not None and not content_html and not title:
        kind = KIND_RATING
    if kind == KIND_RATING and (content_html or title):
        kind = KIND_REVIEW

    enrichment: dict[str, Any] = {
        "slag": kind,
        "tittel": title or None,
        "vurdering": rating,
        "innhald": content_html or None,
        "sitat": quote_html or None,
        "posisjon": _position(document.get("position")),
        "sluttposisjon": _position(document.get("endposition")),
        "posisjonsmodus": _position_mode(document.get("positionMode")),
        "status": None,
        "sensitiv": bool(document.get("sensitive")),
        "aatvaring": sanitise.clean_text(document.get("summary"), limit=300) or None,
        "bok_url": book_url,
        "bok": None,
        "kjelde": identifier or uri or None,
    }
    if kind == KIND_READING_STATUS:
        # The machine-readable field when the instance sends one, the generated
        # prose when it does not.
        shelf = document.get("readingStatus")
        enrichment["status"] = (
            _READING_STATUS_FIELD.get(str(shelf).strip().lower())
            if isinstance(shelf, str)
            else None
        ) or _reading_state(document.get("content") or "")
    return enrichment


async def _fetch_one(uri: str) -> dict[str, Any] | None:
    host = netfetch.normalise_domain(urlsplit(uri).hostname or "")
    # The allowlist gate. No nodeinfo-confirmed BookWyrm entry, no fetch —
    # without this the endpoint is an open proxy (ADR 0003).
    if not host or not instances.is_confirmed_bookwyrm(host):
        return None
    try:
        fetched = await netfetch.fetch(
            uri,
            allowed_hosts={host},
            accept=books.AP_ACCEPT,
            max_bytes=config.MAX_JSON_BYTES,
        )
        document = json.loads(fetched.body.decode("utf-8", "replace"))
    except (netfetch.FetchError, ValueError):
        return None
    return parse_object(document, host, uri)


async def _enrich_one(uri: str) -> dict[str, Any] | None:
    async with _semaphore:
        enrichment = await _fetch_one(uri)
    if enrichment is None:
        return None
    book_url = enrichment.pop("bok_url", None)
    if book_url:
        record = await books.ensure_book(book_url)
        if record:
            enrichment["bok"] = record["id"]
    return enrichment


async def enrich(uris: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Enrich a batch of status URIs.

    Returns (enrichment by URI, book records by id). Unknown or unfetchable URIs
    come back as null rather than an error: one bad post must not fail a screen.
    """
    wanted: list[str] = []
    for raw in uris[: config.MAX_URIS_PER_REQUEST]:
        if isinstance(raw, str) and raw.startswith("https://") and raw not in wanted:
            wanted.append(raw)

    results: dict[str, Any] = {}
    misses: list[str] = []
    for uri in wanted:
        cached = _cache.get(uri)
        if cached is NOT_A_BOOK_POST:
            results[uri] = None
        elif cached is not None:
            results[uri] = cached
        else:
            misses.append(uri)

    if misses:
        fetched = await asyncio.gather(
            *(_enrich_one(uri) for uri in misses), return_exceptions=True
        )
        for uri, outcome in zip(misses, fetched):
            enrichment = None if isinstance(outcome, BaseException) else outcome
            _cache.put(uri, enrichment if enrichment is not None else NOT_A_BOOK_POST)
            results[uri] = enrichment

    book_ids = {value["bok"] for value in results.values() if value and value.get("bok")}
    book_records: dict[str, Any] = {}
    for identifier in book_ids:
        record = db.get_book(identifier)
        if record:
            book_records[identifier] = books.public_book(record)
    return results, book_records


def cache_stats() -> dict[str, Any]:
    """Sizes only — the keys are post URIs and never leave this process."""
    return _cache.stats()
