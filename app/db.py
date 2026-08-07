"""SQLite storage: instance nodeinfo results and bibliographic data.

Two tables, and it is worth being precise about why only these two exist.

`instance` is infrastructure metadata — which fediverse server runs which
software. `book` is bibliographic data — a book edition is not anyone's personal
information. Neither is tied to a reader.

What is deliberately absent: users, tokens, sessions, follow graphs, and any
record of who viewed what. Post enrichment lives in an in-memory TTL cache
(app/cache.py) and is never written here. If you find yourself adding a table
with a person in it, stop and read docs/decision-records/0002 first.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections.abc import Mapping
from typing import Any, Iterable

from . import config

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS instance (
    domain           TEXT PRIMARY KEY,
    software_name    TEXT,
    software_version TEXT,
    is_bookwyrm      INTEGER NOT NULL DEFAULT 0,
    probed_at        REAL    NOT NULL
);

-- `id` is a deterministic digest of `ap_url` (books.book_id), so it is the only
-- uniqueness constraint the table needs. Do NOT add UNIQUE to ap_url as well:
-- the upsert below targets one conflict index, and a second unique index that
-- always collides at the same time would raise instead of updating.
CREATE TABLE IF NOT EXISTS book (
    id           TEXT PRIMARY KEY,
    ap_url       TEXT NOT NULL,
    title        TEXT,
    subtitle     TEXT,
    authors      TEXT,           -- JSON array of names
    pages        INTEGER,
    isbn         TEXT,
    description  TEXT,
    bookwyrm_url TEXT,
    cover_file   TEXT,
    blurhash     TEXT,
    fetched_at   REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS book_fetched_at ON book (fetched_at);
CREATE INDEX IF NOT EXISTS book_ap_url ON book (ap_url);
"""


def connect() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            config.COVER_DIR.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.executescript(SCHEMA)
            conn.commit()
            _conn = conn
        return _conn


def close() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None


def _bind(params: Iterable[Any] | Mapping[str, Any]) -> Any:
    """Pass a mapping through untouched; make anything else a tuple.

    `tuple(some_dict)` yields the dict's *keys*, so a named-placeholder
    statement bound that way silently inserts the column names as values. That
    is exactly what happened here once — every cached book came back as the row
    ('id', 'title') — so the two cases stay explicit.
    """
    if isinstance(params, Mapping):
        return params
    return tuple(params)


def _query(sql: str, params: Iterable[Any] | Mapping[str, Any] = ()) -> list[sqlite3.Row]:
    conn = connect()
    with _lock:
        return list(conn.execute(sql, _bind(params)))


def _write(sql: str, params: Iterable[Any] | Mapping[str, Any] = ()) -> None:
    conn = connect()
    with _lock:
        conn.execute(sql, _bind(params))
        conn.commit()


def row_count() -> int:
    """Total stored rows, for `/health` (naustet-server ADR 0022).

    A real query rather than a ping: it proves the file is open, the schema is
    there, and SQLite can actually read it. Deliberately one bare cardinal and
    not a per-table breakdown — a public health response gets counts, never a
    description of the schema.
    """
    rows = _query("SELECT (SELECT count(*) FROM book) + (SELECT count(*) FROM instance) AS n")
    return int(rows[0]["n"])


# ── instances ────────────────────────────────────────────────────────────────

def get_instance(domain: str) -> dict[str, Any] | None:
    rows = _query("SELECT * FROM instance WHERE domain = ?", (domain,))
    if not rows:
        return None
    row = rows[0]
    return {
        "domain": row["domain"],
        "software_name": row["software_name"],
        "software_version": row["software_version"],
        "is_bookwyrm": bool(row["is_bookwyrm"]),
        "probed_at": row["probed_at"],
    }


def get_instances(domains: Iterable[str]) -> dict[str, dict[str, Any]]:
    domains = list(domains)
    if not domains:
        return {}
    marks = ",".join("?" * len(domains))
    rows = _query(f"SELECT * FROM instance WHERE domain IN ({marks})", domains)
    return {
        row["domain"]: {
            "domain": row["domain"],
            "software_name": row["software_name"],
            "software_version": row["software_version"],
            "is_bookwyrm": bool(row["is_bookwyrm"]),
            "probed_at": row["probed_at"],
        }
        for row in rows
    }


def put_instance(
    domain: str,
    software_name: str | None,
    software_version: str | None,
    is_bookwyrm: bool,
) -> None:
    _write(
        """
        INSERT INTO instance (domain, software_name, software_version, is_bookwyrm, probed_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(domain) DO UPDATE SET
            software_name    = excluded.software_name,
            software_version = excluded.software_version,
            is_bookwyrm      = excluded.is_bookwyrm,
            probed_at        = excluded.probed_at
        """,
        (domain, software_name, software_version, int(is_bookwyrm), time.time()),
    )


def instance_is_fresh(record: dict[str, Any]) -> bool:
    ttl = config.INSTANCE_TTL if record["is_bookwyrm"] else config.INSTANCE_NEGATIVE_TTL
    return (time.time() - record["probed_at"]) < ttl


# ── books ────────────────────────────────────────────────────────────────────

def get_book(book_id: str) -> dict[str, Any] | None:
    rows = _query("SELECT * FROM book WHERE id = ?", (book_id,))
    return _book_row(rows[0]) if rows else None


def get_book_by_url(ap_url: str) -> dict[str, Any] | None:
    rows = _query("SELECT * FROM book WHERE ap_url = ?", (ap_url,))
    return _book_row(rows[0]) if rows else None


def _book_row(row: sqlite3.Row) -> dict[str, Any]:
    try:
        authors = json.loads(row["authors"] or "[]")
    except ValueError:
        authors = []
    return {
        "id": row["id"],
        "ap_url": row["ap_url"],
        "title": row["title"],
        "subtitle": row["subtitle"],
        "authors": authors,
        "pages": row["pages"],
        "isbn": row["isbn"],
        "description": row["description"],
        "bookwyrm_url": row["bookwyrm_url"],
        "cover_file": row["cover_file"],
        "blurhash": row["blurhash"],
        "fetched_at": row["fetched_at"],
    }


def put_book(book: dict[str, Any]) -> None:
    _write(
        """
        INSERT INTO book (id, ap_url, title, subtitle, authors, pages, isbn,
                          description, bookwyrm_url, cover_file, blurhash, fetched_at)
        VALUES (:id, :ap_url, :title, :subtitle, :authors, :pages, :isbn,
                :description, :bookwyrm_url, :cover_file, :blurhash, :fetched_at)
        ON CONFLICT(id) DO UPDATE SET
            title        = excluded.title,
            subtitle     = excluded.subtitle,
            authors      = excluded.authors,
            pages        = excluded.pages,
            isbn         = excluded.isbn,
            description  = excluded.description,
            bookwyrm_url = excluded.bookwyrm_url,
            cover_file   = COALESCE(excluded.cover_file, book.cover_file),
            blurhash     = COALESCE(excluded.blurhash, book.blurhash),
            fetched_at   = excluded.fetched_at
        """,
        {
            "id": book["id"],
            "ap_url": book["ap_url"],
            "title": book.get("title"),
            "subtitle": book.get("subtitle"),
            "authors": json.dumps(book.get("authors") or [], ensure_ascii=False),
            "pages": book.get("pages"),
            "isbn": book.get("isbn"),
            "description": book.get("description"),
            "bookwyrm_url": book.get("bookwyrm_url"),
            "cover_file": book.get("cover_file"),
            "blurhash": book.get("blurhash"),
            "fetched_at": time.time(),
        },
    )
