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
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import config, db, enrich, instances, main, netfetch, outbox, ratelimit

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
            # BookWyrm names the cover attachment after the edition, which is
            # where author and title come from before anything is fetched.
            "attachment": [{
                "type": "Document",
                "url": f"https://{HOST}/images/covers/9.jpg",
                "name": "Sigrid Undset: Kransen (Paperback, 1920, Aschehoug)",
            }],
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
    # Every module-level cache, or one test's fetches satisfy the next one's and
    # the `fetched` assertions quietly stop meaning anything.
    outbox._actors.clear()
    outbox._pages.clear()
    enrich._cache.clear()
    # The per-IP bucket is module-level too, and a whole test module's worth of
    # requests from one address will exhaust the burst and start answering 429 —
    # which shows up as a baffling KeyError on the response body, not as a
    # rate-limit failure. Give every test a full bucket.
    monkeypatch.setattr(
        ratelimit, "buckets", ratelimit.TokenBuckets(config.RATE_PER_SEC, config.RATE_BURST)
    )

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


def test_every_card_carries_the_origins_publication_time(served) -> None:
    """Without this the client sorts on NaN and every card dates from 1970.

    The timeline feed read the date off the Mastodon status, so nothing here ever
    needed it; the outbox feed has no other source.
    """
    client, _ = served
    allowlist()

    body = client.post("/api/samling", json={"aktor": ACTOR, "side": 1}).json()
    assert body["innslag"], "expected cards"
    for entry in body["innslag"]:
        assert entry["publisert"], f"no publication time on {entry['kjelde']}"
        # Parseable, not merely present.
        datetime.fromisoformat(entry["publisert"].replace("Z", "+00:00"))


def test_unparseable_publication_times_become_null_not_rubbish(served) -> None:
    """`Date.parse` of a bad string is silently NaN, which renders as 1970."""
    for bad in ("", "  ", "not a date", "2026-13-45T99:99:99Z", None, 12345):
        parsed = enrich.parse_object(
            {"id": f"{ACTOR}/comment/9", "type": "Note", "published": bad,
             "content": "<p>x</p>", "inReplyToBook": f"https://{HOST}/book/9"},
            HOST,
            f"{ACTOR}/comment/9",
        )
        assert parsed["publisert"] is None


def test_a_card_is_complete_before_its_edition_is_fetched(served) -> None:
    """Author and title come off the cover attachment's name (`bok_kladd`).

    This is what removed the ~23 s wait: the page no longer blocks on edition
    fetches, author fetches and cover re-encodes to say what book it is about.
    """
    client, _ = served
    allowlist()

    body = client.post("/api/samling", json={"aktor": ACTOR, "side": 1}).json()
    by_uri = {entry["kjelde"]: entry for entry in body["innslag"]}
    draft = by_uri[f"{ACTOR}/comment/2"]["bok_kladd"]
    assert draft["tittel"] == "Kransen"
    assert draft["forfattarar"] == ["Sigrid Undset"]
    assert draft["format"] == "Paperback"
    assert draft["aar"] == 1920
    # And the book id is knowable without a fetch, so the client can ask for the
    # full record once it exists.
    assert by_uri[f"{ACTOR}/comment/2"]["bok"]


@pytest.mark.parametrize(
    "name,expected",
    [
        (
            "Matt Dinniman: This Inevitable Ruin (Hardcover, 2026, Michael Joseph Ltd)",
            {"tittel": "This Inevitable Ruin", "forfattarar": ["Matt Dinniman"],
             "format": "Hardcover", "aar": 2026},
        ),
        (
            "Alice Oseman: Heartstopper (GraphicNovel, 2026, Hodder Children's Books)",
            {"tittel": "Heartstopper", "forfattarar": ["Alice Oseman"],
             "format": "GraphicNovel", "aar": 2026},
        ),
        # No author segment at all.
        ("Kransen", {"tittel": "Kransen", "forfattarar": [], "format": None, "aar": None}),
        # Two authors.
        (
            "Ann Doe, Bo Roe: Saman (Paperback, 1999, X)",
            {"tittel": "Saman", "forfattarar": ["Ann Doe", "Bo Roe"],
             "format": "Paperback", "aar": 1999},
        ),
        # A parenthesis that is part of the title, with nothing recognisable in it.
        (
            "A Writer: A Book (Which Is Long)",
            {"tittel": "A Book", "forfattarar": ["A Writer"], "format": None, "aar": None},
        ),
    ],
)
def test_edition_names_parse(name: str, expected: dict[str, Any]) -> None:
    """The shape is BookWyrm's own `Edition.__str__`; mirrors bokhylla's parser."""
    assert enrich._edition_from_name(name) == expected


def test_a_nonsense_attachment_name_yields_no_draft() -> None:
    for bad in (None, "", "   ", 42, {"a": 1}):
        assert enrich._edition_from_name(bad) is None


def test_the_internal_book_url_never_reaches_the_client(served) -> None:
    """`_bok_url` is our bookkeeping for post-response resolution, not a field."""
    client, _ = served
    allowlist()

    samling = client.post("/api/samling", json={"aktor": ACTOR, "side": 1}).json()
    assert not any(k.startswith("_") for entry in samling["innslag"] for k in entry)

    # The same entries are served from the shared cache by /api/berik.
    berik = client.post("/api/berik", json={"uriar": [f"{ACTOR}/comment/2"]}).json()
    for entry in berik["innslag"].values():
        if entry:
            assert not any(k.startswith("_") for k in entry)


def test_unresolved_editions_are_omitted_not_404(served) -> None:
    """A card whose edition is still being fetched must not look like an error."""
    client, _ = served
    allowlist()

    samling = client.post("/api/samling", json={"aktor": ACTOR, "side": 1}).json()
    ids = [entry["bok"] for entry in samling["innslag"] if entry.get("bok")]
    assert ids

    response = client.post("/api/boker", json={"ider": ids + ["deadbeef"]})
    assert response.status_code == 200
    assert "deadbeef" not in response.json()["boker"]
    assert response.headers["cache-control"] == "no-store"


def test_boker_rejects_bad_bodies_and_sanitises_ids(served) -> None:
    client, _ = served
    assert client.post("/api/boker", json={"ider": "nope"}).status_code == 400
    assert client.post("/api/boker", content=b"{not json").status_code == 400
    # Ids go straight into a lookup, so they are filtered to hex like /api/bok.
    assert client.post(
        "/api/boker", json={"ider": ["../../etc/passwd", 7, None, "' OR 1=1--"]}
    ).json()["boker"] == {}


def test_a_second_reader_does_not_refetch_the_same_page(served) -> None:
    """Two readers following the same popular account: one origin fetch."""
    client, fetched = served
    allowlist()

    client.post("/api/samling", json={"aktor": ACTOR, "side": 1})
    enrich._cache.clear()  # a different reader's posts are not cached for them
    before = fetched.count(f"{OUTBOX}?page=1")
    client.post("/api/samling", json={"aktor": ACTOR, "side": 1})

    assert fetched.count(f"{OUTBOX}?page=1") == before == 1


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
    """The allowlist gate, as on /api/berik: no nodeinfo entry, no fetch.

    The host here must be one the seed list does not cover — `bookwyrm.social` is
    pre-authorised at boot, so it would prove nothing.
    """
    client, fetched = served
    assert "unconfirmed.example" not in instances.SEED_BOOKWYRM

    response = client.post(
        "/api/samling",
        json={"aktor": "https://unconfirmed.example/user/x", "side": 1},
    )
    assert response.status_code == 400
    assert fetched == []


def test_seeded_instances_are_allowlisted_without_a_probe(served) -> None:
    """The seed is a cache warm-up: no reader should pay for the first probe."""
    client, fetched = served
    assert instances.is_confirmed_bookwyrm("bookwyrm.social")
    assert fetched == []  # seeding makes no network request


def test_seeding_never_overrides_a_real_probe_result(served, monkeypatch) -> None:
    """A host we have found *not* to be BookWyrm must not be resurrected."""
    client, _ = served
    domain = instances.SEED_BOOKWYRM[0]
    db.put_instance(domain, "mastodon", "4.3.0", False)

    instances.seed()

    assert instances.is_confirmed_bookwyrm(domain) is False


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
