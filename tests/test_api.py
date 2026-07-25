"""End-to-end checks over the HTTP surface, with no network involved."""
from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient

from app import db, main


@pytest.fixture()
def client(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    from app import config

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "COVER_DIR", tmp_path / "covers")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    db.close()
    with TestClient(main.app) as test_client:
        yield test_client
    db.close()


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.text == "ok"


def test_security_headers_are_present_and_strict(client: TestClient) -> None:
    headers = client.get("/healthz").headers
    csp = headers["content-security-policy"]
    assert "script-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["x-frame-options"] == "DENY"
    # includeSubDomains would commit every sibling *.msge.no service at once.
    assert "includeSubDomains" not in headers["strict-transport-security"]


def test_robots_and_sitemap_are_served(client: TestClient) -> None:
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert robots.headers["content-type"].startswith("text/plain")
    assert "Sitemap: https://lesesalen.msge.no/sitemap.xml" in robots.text
    assert "Disallow: /api/" in robots.text

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert sitemap.headers["content-type"].startswith("application/xml")
    assert "https://lesesalen.msge.no/" in sitemap.text
    assert "__LASTMOD__" not in sitemap.text  # the placeholder must be stamped


def test_berik_rejects_bad_bodies(client: TestClient) -> None:
    assert client.post("/api/berik", json={"uriar": "nope"}).status_code == 400
    assert client.post("/api/berik", content=b"{not json").status_code == 400


def test_berik_refuses_hosts_that_are_not_confirmed_bookwyrm(client: TestClient) -> None:
    """The allowlist gate: an unknown host must produce a null, not a fetch."""
    response = client.post(
        "/api/berik",
        json={"uriar": ["https://evil.example/user/x/review/1", "http://127.0.0.1/x"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["innslag"]["https://evil.example/user/x/review/1"] is None
    # Non-https URIs are dropped before they are even considered.
    assert "http://127.0.0.1/x" not in body["innslag"]


def test_instansar_rejects_bad_bodies(client: TestClient) -> None:
    assert client.post("/api/instansar", json={"domener": "nope"}).status_code == 400


def test_instansar_ignores_unusable_domains_without_probing(client: TestClient) -> None:
    response = client.post(
        "/api/instansar", json={"domener": ["127.0.0.1", "localhost", "", "[::1]"]}
    )
    assert response.status_code == 200
    assert response.json()["instansar"] == {}


def test_unknown_book_is_404(client: TestClient) -> None:
    assert client.get("/api/bok/deadbeef").status_code == 404
    assert client.get("/omslag/deadbeef").status_code == 404


def test_unknown_routes_are_404_not_the_shell(client: TestClient) -> None:
    assert client.get("/definitely-not-a-route").status_code == 404


def test_rate_limit_eventually_trips(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app import ratelimit

    monkeypatch.setattr(ratelimit, "buckets", ratelimit.TokenBuckets(rate=0.0, burst=3))
    codes = [
        client.post("/api/instansar", json={"domener": []}).status_code for _ in range(6)
    ]
    assert 429 in codes


def test_forwarded_for_uses_the_last_hop() -> None:
    from app import ratelimit

    # Caddy appends the real peer, so a forged prefix must not win.
    headers = {"x-forwarded-for": "1.2.3.4, 9.9.9.9"}
    assert ratelimit.client_ip(headers, "172.18.0.1") == "9.9.9.9"
    assert ratelimit.client_ip({}, "172.18.0.1") == "172.18.0.1"


def test_book_ids_are_sanitised_before_hitting_storage(client: TestClient) -> None:
    # Path traversal in the id must not reach the filesystem.
    assert client.get("/omslag/..%2f..%2fetc%2fpasswd").status_code == 404
    assert main._safe_id("../../etc/passwd") == "ecad"


def test_blurhash_matches_the_reference_encoder() -> None:
    from app import blurhash

    # A flat mid-grey 2x2: DC-only, so the expected string is stable and short.
    encoded = blurhash.encode_rgb([(128, 128, 128)] * 4, 2, 2, 1, 1)
    assert encoded.startswith("00")
    assert len(encoded) == 6


def test_language_negotiation() -> None:
    from app import shell

    assert shell.negotiate_language(None) == "nn"
    assert shell.negotiate_language("en-GB,en;q=0.9") == "en"
    assert shell.negotiate_language("nn,en;q=0.5") == "nn"
    assert shell.negotiate_language("de,fr;q=0.8") == "nn"  # default, not an error


def test_csp_does_not_enforce_trusted_types(client: TestClient) -> None:
    """Regression guard for ADR 0006.

    `require-trusted-types-for 'script'` blanks the entire app in Chromium —
    Svelte builds components by assigning compiled markup to innerHTML. It is a
    tempting directive to add back from a hardening checklist, and it fails in
    only one browser, so the failure is easy to miss.
    """
    csp = client.get("/healthz").headers["content-security-policy"]
    assert "require-trusted-types-for" not in csp


def test_named_parameters_survive_the_round_trip(client: TestClient) -> None:
    """Regression guard: `tuple(mapping)` yields keys, not values.

    Binding the book upsert that way inserted the literal strings 'id' and
    'title' as a row, so every cached book came back as nonsense.
    """
    from app import books, db

    db.put_book(
        {
            "id": "abc123",
            "ap_url": "https://bookwyrm.social/book/1",
            "title": "Kransen",
            "authors": ["Sigrid Undset"],
            "pages": 320,
            "isbn": "9788252000000",
            "bookwyrm_url": "https://bookwyrm.social/book/1",
            "cover_file": None,
            "blurhash": None,
        }
    )
    stored = db.get_book("abc123")
    assert stored is not None
    assert stored["title"] == "Kransen"
    assert stored["authors"] == ["Sigrid Undset"]
    assert stored["pages"] == 320
    assert books.public_book(stored)["tittel"] == "Kransen"
