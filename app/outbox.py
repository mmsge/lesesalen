"""Collecting a followed reader's shelf from their own ActivityPub outbox.

`/api/berik` recovers one post at a time, which is what a timeline needs: the
browser already has the URIs and asks about exactly those. Reading the feed *as*
the outboxes of the people you follow is a different shape of question, and a
much cheaper one.

A BookWyrm actor's outbox serves the same "pure" representation that a
third-party fetch of a single object gets — `type` collapsed to `Note` (or
`Article` for a review), the rich fields folded into the rendered content, and
the object kind recoverable only from the URI segment (ADR 0007). But it serves
**fifteen of them per request**:

    GET https://bookwyrm.social/user/x            → outbox: …/user/x/outbox
    GET https://bookwyrm.social/user/x/outbox     → OrderedCollection, totalItems
    GET https://bookwyrm.social/user/x/outbox?page=1
        → 15 orderedItems, newest first, `next`

With `netfetch`'s one-request-per-domain-per-second politeness that is the
difference between one post per second and fifteen. `enrich.parse_object()`
needs no changes to read them.

Two guards deserve naming, because both are easy to undo while making the code
look tidier:

* **The page number is an integer, never a URL.** The outbox hands us a `next`
  link and it is tempting to pass it back to the browser and accept it on the
  next call. That would turn this endpoint into a way to fetch arbitrary paths on
  an allowlisted host. We build the page URL ourselves from the actor's own
  outbox URL.
* **The outbox must live on the actor's own host.** An actor document is remote
  input. One that points its `outbox` at somebody else's server would make us a
  fetch amplifier aimed at a third party, from inside the allowlist.

Nothing here is written to disk. Parsed posts go into the same in-memory TTL
cache `/api/berik` uses and leave the process with the process (ADR 0005), and no
actor URI is ever logged — it says whose reading somebody is following (ADR 0003).
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, NamedTuple
from urllib.parse import parse_qsl, urlsplit

from . import books, config, db, enrich, instances, netfetch
from .cache import TTLCache

class Shelf(NamedTuple):
    """Where an actor's posts are, how many there are, and how deep it goes."""

    outbox: str
    total: int | None
    last_page: int


# actor URI -> Shelf. Establishing one costs two throttled fetches (the actor
# document, then the collection root); caching it means a deep walk pays that
# once instead of on every page.
_actors: TTLCache[Shelf] = TTLCache(
    max_size=config.ACTOR_CACHE_SIZE, ttl=config.ACTOR_CACHE_TTL
)

# "<actor>#<page>" -> the raw orderedItems of that page.
#
# Two readers who both follow the same popular BookWyrm account should not each
# make that instance serve the same page. Short-lived, size-capped, memory only —
# the same volatility as the enrichment cache, and for the same reason: the keys
# name actors somebody follows (ADR 0005, ADR 0010).
_pages: TTLCache[list[Any]] = TTLCache(
    max_size=config.PAGE_CACHE_SIZE, ttl=config.PAGE_CACHE_TTL
)

# Edition resolution outlives the response that started it, so the tasks need a
# reference of their own or the event loop may collect them mid-flight.
_running: set[asyncio.Task] = set()


def _spawn(coroutine) -> None:
    task = asyncio.create_task(coroutine)
    _running.add(task)
    task.add_done_callback(_running.discard)


class OutboxError(Exception):
    """The actor or its outbox could not be used. Carries a client-safe reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _same_host(url: Any, host: str) -> str | None:
    """A https URL on exactly `host`, or None."""
    if not isinstance(url, str) or not url.startswith("https://"):
        return None
    if netfetch.normalise_domain(urlsplit(url).hostname or "") != host:
        return None
    return url


async def _fetch_json(url: str, host: str) -> Any:
    fetched = await netfetch.fetch(
        url,
        allowed_hosts={host},
        accept=books.AP_ACCEPT,
        max_bytes=config.MAX_JSON_BYTES,
    )
    return json.loads(fetched.body.decode("utf-8", "replace"))


def _page_number(url: Any) -> int | None:
    """The `page=N` of a collection link. Just an integer — the URL is not reused."""
    if not isinstance(url, str):
        return None
    for key, value in parse_qsl(urlsplit(url).query):
        if key == "page" and value.isdigit():
            return int(value)
    return None


async def _resolve_shelf(actor_uri: str, host: str) -> Shelf:
    """Locate the actor's outbox and measure it.

    Two fetches, cached together: the actor document says where the outbox is,
    and the collection root says how big it is. The size is worth the extra
    round-trip — it is what lets the browser show real progress through a shelf
    and stop at the end instead of walking until a page comes back empty.
    """
    cached = _actors.get(actor_uri)
    if cached is not None:
        return cached

    try:
        actor = await _fetch_json(actor_uri, host)
    except (netfetch.FetchError, ValueError) as exc:
        raise OutboxError("aktøren svarte ikkje") from exc
    if not isinstance(actor, dict):
        raise OutboxError("ikkje ein aktør")

    # An actor, not a collection or a note. BookWyrm also flags its own accounts
    # with `bookwyrmUser`, but the nodeinfo allowlist has already established
    # that this host is BookWyrm, so requiring the flag as well would only break
    # on instances that omit it.
    if str(actor.get("type") or "").strip().lower() != "person":
        raise OutboxError("ikkje ein aktør")

    outbox = _same_host(actor.get("outbox"), host)
    if outbox is None:
        raise OutboxError("utboks manglar eller ligg på ein annan vert")

    total: int | None = None
    last_page = config.MAX_OUTBOX_PAGE
    try:
        root = await _fetch_json(outbox, host)
    except (netfetch.FetchError, ValueError):
        root = None  # measurable is nice, not required: fall back to the cap
    if isinstance(root, dict):
        declared = root.get("totalItems")
        if isinstance(declared, int) and declared >= 0:
            total = declared
        end = _page_number(root.get("last"))
        if end is not None:
            last_page = min(max(end, 1), config.MAX_OUTBOX_PAGE)

    shelf = Shelf(outbox=outbox, total=total, last_page=last_page)
    _actors.put(actor_uri, shelf)
    return shelf


def _page_url(outbox: str, page: int) -> str:
    """`?page=N`, built from the outbox we resolved — never from client input."""
    separator = "&" if urlsplit(outbox).query else "?"
    return f"{outbox}{separator}page={page}"


async def _items_of(outbox: str, host: str, page: int) -> list[Any]:
    """One outbox page's items, shared briefly between readers."""
    key = f"{outbox}#{page}"
    cached = _pages.get(key)
    if cached is not None:
        return cached
    items = await _fetch_items(outbox, host, page)
    _pages.put(key, items)
    return items


async def _fetch_items(outbox: str, host: str, page: int) -> list[Any]:
    try:
        document = await _fetch_json(_page_url(outbox, page), host)
    except netfetch.StatusError as exc:
        # Paging past the end is a 404 on BookWyrm, which is an answer, not a fault.
        if exc.status == 404:
            return []
        raise OutboxError("utboksa svarte ikkje") from exc
    except (netfetch.FetchError, ValueError) as exc:
        raise OutboxError("utboksa svarte ikkje") from exc

    if not isinstance(document, dict):
        raise OutboxError("utboksa svarte ikkje")
    items = document.get("orderedItems")
    if not isinstance(items, list):
        return []
    return items[: config.MAX_OUTBOX_ITEMS]


def _parse_item(item: Any, host: str) -> tuple[dict[str, Any], str | None] | None:
    """Parse one outbox entry. Returns (enrichment, edition URL to resolve later).

    Deliberately synchronous and fetch-free. The old version awaited
    `books.ensure_book` per item, which meant a page of fifteen posts mentioning
    eight unseen editions blocked for ~23 s behind edition fetches, author
    fetches, cover downloads and re-encodes — while the outbox page itself had
    already told us the author and title (`enrich.parse_object`, `bok_kladd`).
    So the card is assembled now and the edition is resolved after the response.
    """
    if not isinstance(item, dict):
        return None
    uri = item.get("id")
    if not isinstance(uri, str) or _same_host(uri, host) is None:
        return None  # somebody else's object, boosted into this outbox

    cached = enrich.cached(uri)
    if cached is not None:
        if cached is enrich.NOT_A_BOOK_POST:
            return None
        return cached, cached.get("_bok_url")

    enrichment = enrich.parse_object(item, host, uri)
    if enrichment is None:
        enrich.remember(uri, None)
        return None

    book_url = enrichment.pop("bok_url", None)
    if book_url:
        # The id is a hash of the URL, so it is knowable without fetching
        # anything. The client can therefore ask `/api/bok/<id>` for the full
        # record once it exists, and render `bok_kladd` until then.
        enrichment["bok"] = books.book_id(book_url)
        enrichment["_bok_url"] = book_url  # internal; stripped before the response
    enrich.remember(uri, enrichment)
    return enrichment, book_url


async def _resolve_editions(urls: list[str]) -> None:
    """Fetch the editions a page mentioned, after that page has been served.

    Reader-initiated and bounded: this is not a background job that runs without
    anybody present (ADR 0008), it is the tail of a request that has already
    answered. Failures are swallowed — the card still has author and title.
    """
    semaphore = asyncio.Semaphore(config.EDITION_CONCURRENCY)

    async def one(url: str) -> None:
        async with semaphore:
            try:
                await books.ensure_book(url)
            except Exception:
                pass

    await asyncio.gather(*(one(url) for url in urls), return_exceptions=True)


async def collect(actor_uri: str, page: int) -> dict[str, Any]:
    """One page of a followed actor's outbox, parsed into cards.

    Raises `OutboxError` with a client-safe reason. The allowlist check is the
    same cache-only gate `/api/berik` uses: no nodeinfo-confirmed BookWyrm entry,
    no fetch — so the browser must have asked `/api/instansar` about the domain
    first, exactly as it already does before enriching anything (ADR 0003).
    """
    host = netfetch.normalise_domain(urlsplit(actor_uri).hostname or "")
    if not actor_uri.startswith("https://") or not host:
        raise OutboxError("ugyldig aktør-URI")
    if not instances.is_confirmed_bookwyrm(host):
        raise OutboxError("verten er ikkje ein stadfesta BookWyrm-instans")

    shelf = await _resolve_shelf(actor_uri, host)
    items = await _items_of(shelf.outbox, host, page)

    entries: list[dict[str, Any]] = []
    pending: list[str] = []
    for item in items:
        parsed = _parse_item(item, host)
        if parsed is None:
            continue
        enrichment, book_url = parsed
        entries.append(enrichment)
        if book_url and db.get_book(books.book_id(book_url)) is None:
            pending.append(book_url)

    # Editions already on disk go out with the page; the rest are fetched behind
    # it, so the reader is not kept waiting for a cover re-encode.
    book_records: dict[str, Any] = {}
    for identifier in {entry["bok"] for entry in entries if entry.get("bok")}:
        record = db.get_book(identifier)
        if record:
            book_records[identifier] = books.public_book(record)

    if pending:
        _spawn(_resolve_editions(list(dict.fromkeys(pending))))

    return {
        # `_bok_url` is ours, not the client's business, and it is the one field
        # here that names a URL we fetch.
        "innslag": [
            {key: value for key, value in entry.items() if not key.startswith("_")}
            for entry in entries
        ],
        "boker": book_records,
        # A page with few cards on it is not the end — most of an outbox page can
        # be activity that is not a book post. Only running out of pages is.
        "neste": page + 1 if items and page < shelf.last_page else None,
        "totalt": shelf.total,
        "sider": shelf.last_page,
    }


def cache_stats() -> dict[str, Any]:
    """Sizes only — the keys are actor URIs and never leave this process."""
    return _actors.stats()
