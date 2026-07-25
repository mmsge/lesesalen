"""The outbox walk: `/api/samling` and the guards on it.

No network. Every outbound fetch is served from `SERVED` below, and each test
asserts on `fetched` — the list of URLs the code actually asked for — because
several of the guards here are only observable that way. "It refused" and "it
refused *without* making the request" are different outcomes, and only the
second one is safe.

The fixtures are the real shapes observed from bookwyrm.social (see
`tests/test_enrich.py` for the same convention) with invented content: `type` is
always `Note`, except a review which is an `Article`, and the object kind is only
recoverable from the URI segment (ADR 0007).
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import config, db, enrich, main, netfetch, outbox

HOST = "bookwyrm.social"
ACTOR = f"https://{HOST}/user/lesar"
OUTBOX = f"{ACTOR}/outbox"

ACTOR_DOCUMENT = {
    "id": ACTOR,
    "type": "Person",
    "preferredUsername": "lesar",
    "bookwyrmUser": True,
    "outbox": OUTBOX,
    "followers": f"{ACTOR}/followers",
}

# The collection root: this is the only place `totalItems` and the page count
# live. The actor document carries neither.
OUTBOX_ROOT = {
    "id": OUTBOX,
    "type": "OrderedCollection",
    "totalItems": 1092,
    "first": f"{OUTBOX}?page=1",
    "last": f"{OUTBOX}?page=73",
}

OUTBOX_PAGE_1 = {
    "id": f"{OUTBOX}?page=1",
    "type": "OrderedCollectionPage",
    "partOf": OUTBOX,
    "next": f"{OUTBOX}?page=2",
    "orderedItems": [
        {
            "id": f"{ACTOR}/generatednote/1",
            "type": "Note",
            "published": "2026-07-22T09:51:19+00:00",
            "attributedTo": ACTOR,
            "readingStatus": "reading",
            "content": f'<p>Lesar started reading <a href="https://{HOST}/book/9">Kransen</a></p>',
            "tag": [{"type": "Edition", "href": f"https://{HOST}/book/9"}],
        },
        {
            "id": f"{ACTOR}/comment/2",
            "type": "Note",
            "published": "2026-07-21T09:00:00+00:00",
            "attributedTo": ACTOR,
            "content": "<p>Halvvegs, og det held.</p>",
            "inReplyToBook": f"https://{HOST}/book/9",
        },
        {
            # A review arrives as an Article, and the rating survives only inside
            # `name`.
            "id": f"{ACTOR}/review/3",
            "type": "Article",
            "published": "2026-07-20T09:00:00+00:00",
            "attributedTo": ACTOR,
            "name": 'Review of "Kransen" (4 stars): Eit år i eit menneskeliv',
            "content": "<p>God.</p>",
            "inReplyToBook": f"https://{HOST}/book/9",
        },
        {
            "id": f"{ACTOR}/quotation/4",
            "type": "Note",
            "published": "2026-07-19T09:00:00+00:00",
            "attributedTo": ACTOR,
            "content": "<p>Ei setning verd å ta vare på.</p>",
            "position": 120,
            "inReplyToBook": f"https://{HOST}/book/9",
        },
        {
            # Somebody else's object, boosted into this outbox. Not this reader's
            # post, and not on a host we resolved: it must be dropped.
            "id": "https://another.example/user/x/review/9",
            "type": "Note",
            "attributedTo": "https://another.example/user/x",
            "content": "<p>Frå ein annan vert.</p>",
            "inReplyToBook": "https://another.example/book/1",
        },
        {
            # Not a book post at all: a plain toot from a BookWyrm account.
            "id": f"{ACTOR}/status/5",
            "type": "Note",
            "published": "2026-07-18T09:00:00+00:00",
            "attributedTo": ACTOR,
            "content": "<p>God morgon.</p>",
        },
    ],
}

BOOK_DOCUMENT = {
    "id": f"https://{HOST}/book/9",
    "type": "Edition",
    "title": "Kransen",
    "pages": 320,
}

SERVED: dict[str, Any] = {
    ACTOR: ACTOR_DOCUMENT,
    OUTBOX: OUTBOX_ROOT,
    f"{OUTBOX}?page=1": OUTBOX_PAGE_1,
    f"{OUTBOX}?page=2": {"id": f"{OUTBOX}?page=2", "orderedItems": []},
    f"https://{HOST}/book/9": BOOK_DOCUMENT,
}


@pytest.fixture()
def served(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """A client whose outbound fetches are canned, plus the URLs it asked for."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "COVER_DIR", tmp_path / "covers")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    db.close()

    fetched: list[str] = []

    async def fake_fetch(url: str, *, allowed_hosts, accept: str, max_bytes: int, **_kw):
        fetched.append(url)
        host = netfetch.normalise_domain(url.split("/")[2])
        # The real fetch enforces this and the tests rely on it: a canned server
        # that answers for any host would hide an allowlist bug.
        if host not in allowed_hosts:
            raise netfetch.BlockedError("host not allowed")
        document = SERVED.get(url)
        if document is None:
            raise netfetch.StatusError(404)
        return netfetch.Fetched(
            url=url,
            status=200,
            content_type="application/activity+json",
            body=json.dumps(document).encode("utf-8"),
        )

    monkeypatch.setattr(netfetch, "fetch", fake_fetch)
    outbox._actors.clear()
    enrich._cache.clear()

    with TestClient(main.app) as test_client:
        yield test_client, fetched
    db.close()


def allowlist(domain: str = HOST) -> None:
    """Seed the nodeinfo allowlist the way a prior /api/instansar call would."""
    db.put_instance(domain, "bookwyrm", "0.7.5", True)


# ── the happy path ───────────────────────────────────────────────────────────

def test_one_page_yields_every_book_post_on_it(served) -> None:
    client, fetched = served
    allowlist()

    response = client.post("/api/samling", json={"aktor": ACTOR, "side": 1})
    assert response.status_code == 200
    body = response.json()

    kinds = sorted(entry["slag"] for entry in body["innslag"])
    assert kinds == sorted(
        [
            enrich.KIND_READING_STATUS,
            enrich.KIND_COMMENT,
            enrich.KIND_REVIEW,
            enrich.KIND_QUOTATION,
        ]
    )
    # The plain toot and the other host's object are both gone.
    assert len(body["innslag"]) == 4
    assert not any("another.example" in entry["kjelde"] for entry in body["innslag"])

    # One request bought four cards. That is the entire point of the endpoint:
    # `/api/berik` would have cost one throttled fetch per post.
    assert fetched.count(f"{OUTBOX}?page=1") == 1


def test_uri_segment_still_decides_the_kind(served) -> None:
    """Every item here says `type: Note` or `Article`. Only the URI is truthful."""
    client, _ = served
    allowlist()

    body = client.post("/api/samling", json={"aktor": ACTOR, "side": 1}).json()
    by_uri = {entry["kjelde"]: entry for entry in body["innslag"]}

    assert by_uri[f"{ACTOR}/generatednote/1"]["slag"] == enrich.KIND_READING_STATUS
    assert by_uri[f"{ACTOR}/generatednote/1"]["status"] == "byrja"
    assert by_uri[f"{ACTOR}/comment/2"]["slag"] == enrich.KIND_COMMENT
    assert by_uri[f"{ACTOR}/quotation/4"]["slag"] == enrich.KIND_QUOTATION
    assert by_uri[f"{ACTOR}/quotation/4"]["posisjon"] == 120

    review = by_uri[f"{ACTOR}/review/3"]
    assert review["slag"] == enrich.KIND_REVIEW
    assert review["vurdering"] == 4.0
    assert review["tittel"] == "Eit år i eit menneskeliv"


def test_the_shelf_is_measured_from_the_collection_root(served) -> None:
    """`totalItems` and the page count live on the root, not on the actor."""
    client, fetched = served
    allowlist()

    body = client.post("/api/samling", json={"aktor": ACTOR, "side": 1}).json()
    assert body["totalt"] == 1092
    assert body["sider"] == 73
    assert body["neste"] == 2
    assert fetched.count(OUTBOX) == 1


def test_an_empty_page_ends_the_walk(served) -> None:
    client, _ = served
    allowlist()

    body = client.post("/api/samling", json={"aktor": ACTOR, "side": 2}).json()
    assert body["innslag"] == []
    assert body["neste"] is None


def test_the_shelf_is_resolved_once_across_pages(served) -> None:
    """Paging must not re-fetch the actor and the root every time."""
    client, fetched = served
    allowlist()

    client.post("/api/samling", json={"aktor": ACTOR, "side": 1})
    client.post("/api/samling", json={"aktor": ACTOR, "side": 2})

    assert fetched.count(ACTOR) == 1
    assert fetched.count(OUTBOX) == 1


def test_parsed_posts_warm_the_shared_enrichment_cache(served) -> None:
    """A post collected here must not be re-fetched by /api/berik (ADR 0005)."""
    client, fetched = served
    allowlist()

    client.post("/api/samling", json={"aktor": ACTOR, "side": 1})
    before = len(fetched)

    response = client.post("/api/berik", json={"uriar": [f"{ACTOR}/review/3"]})
    assert response.json()["innslag"][f"{ACTOR}/review/3"]["tittel"] == (
        "Eit år i eit menneskeliv"
    )
    assert len(fetched) == before  # served from memory, no second round-trip


# ── the guards ───────────────────────────────────────────────────────────────

def test_an_actor_on_an_unconfirmed_host_is_refused_without_fetching(served) -> None:
    """The allowlist gate, as on /api/berik: no nodeinfo entry, no fetch."""
    client, fetched = served
    # Deliberately no allowlist() call.

    response = client.post("/api/samling", json={"aktor": ACTOR, "side": 1})
    assert response.status_code == 400
    assert fetched == []


def test_a_non_bookwyrm_host_is_refused_even_when_probed(served) -> None:
    client, fetched = served
    db.put_instance("mastodon.social", "mastodon", "4.3.0", False)

    response = client.post(
        "/api/samling",
        json={"aktor": "https://mastodon.social/users/someone", "side": 1},
    )
    assert response.status_code == 400
    assert fetched == []


def test_an_outbox_on_another_host_is_refused(served, monkeypatch) -> None:
    """Remote input: an actor pointing elsewhere would make us an amplifier."""
    client, fetched = served
    allowlist()
    monkeypatch.setitem(
        SERVED, ACTOR, {**ACTOR_DOCUMENT, "outbox": "https://elsewhere.example/outbox"}
    )

    response = client.post("/api/samling", json={"aktor": ACTOR, "side": 1})
    assert response.status_code == 400
    assert "elsewhere.example" not in " ".join(fetched)


def test_something_that_is_not_an_actor_is_refused(served) -> None:
    client, _ = served
    allowlist()

    response = client.post(
        "/api/samling", json={"aktor": f"https://{HOST}/book/9", "side": 1}
    )
    assert response.status_code == 400


def test_an_actor_without_an_outbox_is_refused(served, monkeypatch) -> None:
    client, _ = served
    allowlist()
    without = {key: value for key, value in ACTOR_DOCUMENT.items() if key != "outbox"}
    monkeypatch.setitem(SERVED, ACTOR, without)

    assert client.post("/api/samling", json={"aktor": ACTOR, "side": 1}).status_code == 400


@pytest.mark.parametrize(
    "page", [0, -1, config.MAX_OUTBOX_PAGE + 1, 10**9, True, 1.5, "1", None]
)
def test_the_page_must_be_a_bounded_integer(served, page: Any) -> None:
    """`side` becomes part of a URL we build, so it is validated, not trusted.

    `True` is in here on purpose: `bool` is an `int` in Python, and without the
    explicit check `side: true` would page an outbox.
    """
    client, fetched = served
    allowlist()

    response = client.post("/api/samling", json={"aktor": ACTOR, "side": page})
    assert response.status_code == 400
    assert fetched == []


def test_no_client_supplied_url_is_ever_fetched(served) -> None:
    """The outbox hands us a `next` link; we must build the page URL ourselves.

    Accepting a URL from the caller would make this endpoint a way to fetch
    arbitrary paths on an allowlisted host.
    """
    client, fetched = served
    allowlist()

    client.post(
        "/api/samling",
        json={
            "aktor": ACTOR,
            "side": 1,
            # All ignored: the endpoint has no parameter that takes a URL.
            "neste": f"https://{HOST}/admin/settings",
            "utboks": "https://elsewhere.example/outbox",
            "url": f"https://{HOST}/api/secrets",
        },
    )
    for url in fetched:
        assert "elsewhere.example" not in url
        assert "/admin/settings" not in url
        assert "/api/secrets" not in url

    # Everything fetched is either the shelf we resolved ourselves, or a book
    # lookup on a host `config.FALLBACK_HOSTS` already permits.
    shelf_urls = {ACTOR, OUTBOX, f"{OUTBOX}?page=1", f"https://{HOST}/book/9"}
    for url in fetched:
        host = netfetch.normalise_domain(url.split("/")[2])
        assert url in shelf_urls or host in config.FALLBACK_HOSTS


def test_scheme_and_shape_of_the_actor_uri(served) -> None:
    client, fetched = served
    allowlist()

    for actor in ("http://bookwyrm.social/user/x", f"https://127.0.0.1/user/x", "", "x"):
        assert client.post("/api/samling", json={"aktor": actor}).status_code == 400
    assert fetched == []


def test_samling_rejects_bad_bodies(served) -> None:
    client, _ = served
    assert client.post("/api/samling", json={"aktor": 7}).status_code == 400
    assert client.post("/api/samling", json={}).status_code == 400
    assert client.post("/api/samling", content=b"{not json").status_code == 400


def test_an_absurd_page_is_truncated_before_parsing(served, monkeypatch) -> None:
    """A hostile origin answering with thousands of items must not be parsed."""
    client, _ = served
    allowlist()
    flood = {
        "id": f"{OUTBOX}?page=1",
        "orderedItems": [
            {
                "id": f"{ACTOR}/comment/{n}",
                "type": "Note",
                "content": "<p>x</p>",
                "inReplyToBook": f"https://{HOST}/book/9",
            }
            for n in range(5000)
        ],
    }
    monkeypatch.setitem(SERVED, f"{OUTBOX}?page=1", flood)

    body = client.post("/api/samling", json={"aktor": ACTOR, "side": 1}).json()
    assert len(body["innslag"]) <= config.MAX_OUTBOX_ITEMS


# ── nothing is stored ────────────────────────────────────────────────────────

def test_collecting_a_shelf_stores_no_posts(served) -> None:
    """The tell that ADR 0002/0008 has been undone is a table with posts in it."""
    client, _ = served
    allowlist()

    client.post("/api/samling", json={"aktor": ACTOR, "side": 1})

    tables = {
        row["name"]
        for row in db.connect().execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    assert tables <= {"instance", "book", "sqlite_sequence"}

    # And no actor or post URI is anywhere in the book rows either.
    rows = db.connect().execute("SELECT * FROM book").fetchall()
    for row in rows:
        assert ACTOR not in " ".join(str(value) for value in tuple(row))


def test_actor_cache_stats_expose_sizes_only(served) -> None:
    client, _ = served
    allowlist()
    client.post("/api/samling", json={"aktor": ACTOR, "side": 1})

    stats = outbox.cache_stats()
    assert set(stats) == {"entries", "max", "ttl"}
    assert ACTOR not in json.dumps(stats)
