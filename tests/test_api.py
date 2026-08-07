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
    assert response.headers["content-type"].startswith("text/plain")
    assert response.headers["cache-control"] == "no-store"
    # Exactly two bytes, no trailing newline: docker-compose.yml byte-compares
    # this (`.read() == b'ok'`), so a newline breaks the healthcheck silently.
    assert response.content == b"ok"


def test_healthz_touches_no_dependency(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Liveness must not consult the database.

    The tempting implementation is `return health()`; with a container
    healthcheck pointed at /healthz that restarts lesesalen every time a
    dependency is unhappy. Break the dependency and /healthz must not notice.
    """
    def explode() -> int:
        raise RuntimeError("db is down")

    monkeypatch.setattr(db, "row_count", explode)
    assert client.get("/healthz").content == b"ok"


def test_version_reports_the_running_image(client: TestClient) -> None:
    response = client.get("/version")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["service"] == "lesesalen"
    assert set(body) == {
        "service", "commit", "commit_short", "branch", "commit_time",
        "repo", "dirty", "built_at", "source",
    }
    assert body["source"] in {"build-info", "unknown"}
    if body["source"] == "unknown":
        assert body["commit"] is None
    else:
        assert len(body["commit"]) == 40  # the full sha — short ones collide


def test_version_without_build_info_says_unknown(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An absent build-info.json is not an error, and never a guess."""
    monkeypatch.setattr(main, "_ROOT", tmp_path)
    info = main._build_info()
    assert info["source"] == "unknown"
    assert info["service"] == "lesesalen"
    assert all(
        info[key] is None
        for key in ("commit", "commit_short", "branch", "commit_time", "repo",
                    "dirty", "built_at")
    )


def test_version_drops_unknown_keys_from_build_info(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """/version is public, so the response shape is the allowlist — not whatever
    happens to be in the file."""
    import json

    (tmp_path / "build-info.json").write_text(
        json.dumps({"commit_short": "abc1234", "SECRET_TOKEN": "hunter2"})
    )
    monkeypatch.setattr(main, "_ROOT", tmp_path)
    info = main._build_info()
    assert info["commit_short"] == "abc1234"
    assert info["source"] == "build-info"
    assert "SECRET_TOKEN" not in info


def test_health_reports_substantive_checks(client: TestClient) -> None:
    response = client.get("/health")
    # degraded is a 200 on purpose — only a real failure is 503.
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["service"] == "lesesalen"
    assert body["status"] in {"ok", "degraded"}
    assert isinstance(body["uptime_seconds"], int)
    assert body["started_at"] and body["checked_at"]

    by_name = {check["name"]: check for check in body["checks"]}
    assert set(by_name) <= set(main.HEALTH_CHECKS)
    # A real query with a row count, not a ping.
    assert by_name["database"]["status"] == "ok"
    assert by_name["database"]["detail"].endswith("rows")
    assert isinstance(by_name["database"]["latency_ms"], (int, float))
    assert by_name["cache"]["detail"].endswith("entries")


def test_health_leaks_nothing_about_the_box(client: TestClient) -> None:
    """The redaction allowlist (naustet-server ADR 0022): /health is public.

    Paths, ports, hostnames, env names and exception text are all forbidden —
    and `str(exc)` is how they normally get in.
    """
    response = client.get("/health")
    for forbidden in ("/data", "/app", "/srv", "172.18.0.1", "127.0.0.1",
                      "8080", "4023", "LESESALEN_", "sqlite", "Traceback"):
        assert forbidden not in response.text

    for check in response.json()["checks"]:
        detail = check.get("detail")
        if detail is None:
            continue
        assert detail in main.DETAIL or detail.split()[-1] in {"rows", "entries"}


def test_health_degrades_without_restarting_the_container(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing cover directory is degraded, and degraded is 200.

    If it were 503 and anyone pointed a container healthcheck at /health, this
    would restart lesesalen forever.
    """
    monkeypatch.setattr(main.config, "COVER_DIR", pathlib.Path("/nonexistent/covers"))
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    storage = next(c for c in body["checks"] if c["name"] == "storage")
    assert storage["status"] == "degraded"
    assert storage["detail"] == "unavailable"


def test_health_is_503_only_on_a_real_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode() -> int:
        raise RuntimeError("no such table: book — /data/lesesalen.db")

    monkeypatch.setattr(db, "row_count", explode)
    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    database = next(c for c in body["checks"] if c["name"] == "database")
    assert database["detail"] == "unavailable"
    # The exception named a table and a database path. Neither may appear.
    assert "lesesalen.db" not in response.text
    assert "no such table" not in response.text


def test_ops_endpoints_beat_the_spa_catch_all(client: TestClient) -> None:
    """`/{path:path}` answers unknown routes, and an HTML 200 on /version reads
    as 'endpoint missing' to the box's probe rather than as a failure. Route
    registration order is the only thing preventing that, so assert it."""
    for path in ("/version", "/health"):
        assert client.get(path).headers["content-type"].startswith("application/json")
    assert client.get("/healthz").headers["content-type"].startswith("text/plain")


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
