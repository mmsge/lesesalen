"""Lesesalen's HTTP surface.

Four API endpoints, all unauthenticated, none of which carry a token or a reader
identity — plus the static client and the box's required files.

Three of them accept nothing that names a person: bare domain names, post URIs
and book ids. `/api/samling` is the exception and is the reason ADR 0008 exists:
it takes the URI of an actor somebody follows. Same discipline applies — no log
line, no storage, `no-store` on the way out.

The security headers below are set here rather than in Caddy on purpose: they
are application-specific (they describe *this* app's script and connection
model), and the box convention keeps service config out of central ingress.
"""
from __future__ import annotations

import contextlib
import mimetypes
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse

from . import books, config, db, enrich, instances, netfetch, outbox, ratelimit, shell

_shell: shell.Shell | None = None


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    global _shell
    db.connect()
    instances.seed()
    _shell = shell.Shell()
    yield
    await netfetch.aclose()
    db.close()


app = FastAPI(
    title="Lesesalen",
    docs_url=None,          # no interactive docs: they would need inline script
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

# The client's own route table (design 5g). Anything not listed here is a 404
# rather than a shell, so a typo does not silently render an empty app.
#
# `/attende` is the OAuth redirect URI registered with instances people have
# already logged in through; it cannot be dropped without breaking them, so it
# stays alongside the newer `/logg-inn/attende`. `/lesar/` is the old person
# route, kept for links already shared — the client redirects it to `/@`.
SPA_ROUTES = {
    "/",
    "/om",
    "/personvern",
    "/attende",
    "/innstillingar",
    "/logg-inn",
    "/logg-inn/attende",
}
SPA_PREFIXES = ("/lesar/", "/innlegg/", "/bok/", "/@")

# ── security headers ─────────────────────────────────────────────────────────
#
# The token lives in the browser's localStorage, so one successful XSS is a full
# account compromise for whoever is using the app. `script-src 'self'` and
# `object-src 'none'` are the directives that actually stop that, and they are
# the ones never to loosen: no 'unsafe-inline', no 'unsafe-eval', ever — not
# even briefly, during a frustrating debugging session.
#
# Two directives are deliberately broad, and it is worth knowing why so nobody
# "tightens" them into breaking the app:
#   connect-src https:  the reader's instance is arbitrary and unknown when this
#                       header is written. It cannot be enumerated.
#   img-src https:      avatars and media come from that same unknown instance.
CSP = "; ".join(
    [
        "default-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' https: data:",
        "font-src 'self'",
        "connect-src 'self' https:",
        "manifest-src 'self'",
        "base-uri 'none'",
        "form-action 'none'",
        "frame-ancestors 'none'",
        "object-src 'none'",
        "upgrade-insecure-requests",
        # `require-trusted-types-for 'script'` is deliberately NOT here. It reads
        # like a cheap backstop, and in Chromium it is fatal: Svelte builds every
        # component by assigning its compiled markup to `innerHTML`, so enforcing
        # Trusted Types blanks the whole app with "This document requires
        # 'TrustedHTML' assignment" — in Chromium only, while Firefox looks fine.
        # A default Trusted Types policy cannot rescue it either: it would have to
        # pass Svelte's own templates through untouched, comment anchors and all,
        # which is precisely what a sanitising policy strips. See ADR 0006 before
        # adding it back.
    ]
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    # No `includeSubDomains`: this host is one label under msge.no and the
    # directive would commit every sibling subdomain on the box at once. That is
    # a decision for hetzner-server to make for the apex, not for a tenant to
    # make on its behalf. No `preload` either — it is effectively irreversible.
    "Strict-Transport-Security": "max-age=31536000",
}


@app.middleware("http")
async def security_and_limits(request: Request, call_next):
    path = request.url.path
    # Only the API is metered. /omslag/ serves local, immutable, already-cached
    # files and a feed legitimately asks for twenty of them at once — metering
    # it would throttle normal reading without protecting anything.
    if path.startswith("/api/"):
        who = ratelimit.client_ip(request.headers, request.client.host if request.client else None)
        if not ratelimit.buckets.allow(who):
            response: Response = JSONResponse(
                {"feil": "for mange førespurnader"}, status_code=429,
                headers={"Retry-After": "5"},
            )
            for header, value in SECURITY_HEADERS.items():
                response.headers.setdefault(header, value)
            return response
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response


# ── box requirements ─────────────────────────────────────────────────────────

@app.api_route("/healthz", methods=["GET", "HEAD"], response_class=PlainTextResponse)
async def healthz() -> str:
    return "ok"


@app.api_route("/robots.txt", methods=["GET", "HEAD"])
async def robots_txt() -> Response:
    served = shell.static_file("robots.txt")
    if served is None:
        return PlainTextResponse("User-agent: *\nDisallow:\n", media_type="text/plain")
    return Response(served["body"], media_type="text/plain; charset=utf-8")


@app.api_route("/sitemap.xml", methods=["GET", "HEAD"])
async def sitemap_xml() -> Response:
    served = shell.static_file("sitemap.xml")
    if served is None:
        return Response("not found", status_code=404)
    return Response(served["body"], media_type="application/xml; charset=utf-8")


# ── the API ──────────────────────────────────────────────────────────────────

@app.post("/api/instansar")
async def api_instansar(request: Request) -> Response:
    """In: bare domain names. Out: which of them run BookWyrm.

    The browser sends domains, never a follow list. A domain is infrastructure,
    not a person, and one probe answers for everybody.
    """
    payload = await _json_body(request)
    if payload is None:
        return JSONResponse({"feil": "ugyldig JSON"}, status_code=400)
    raw = payload.get("domener")
    if not isinstance(raw, list):
        return JSONResponse({"feil": "domener må vera ei liste"}, status_code=400)

    described = await instances.describe([d for d in raw if isinstance(d, str)])
    return JSONResponse(
        {
            "instansar": {
                domain: {
                    "bookwyrm": record["is_bookwyrm"],
                    "programvare": record["software_name"],
                    # The login screen names the software it found before asking
                    # anyone to leave the app ("Mastodon 4.3"). It is the
                    # instance's own public nodeinfo, about the host and not
                    # about a person, and the same probe already answers for
                    # everybody who asks.
                    "versjon": record.get("software_version"),
                }
                for domain, record in described.items()
            }
        },
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.post("/api/berik")
async def api_berik(request: Request) -> Response:
    """In: BookWyrm status URIs. Out: parsed enrichment plus book records.

    These URIs describe what somebody is reading. They pass through memory and
    leave no trace: no log line here, and uvicorn's access log is off in the
    Dockerfile CMD for the same reason (ADR 0003).
    """
    payload = await _json_body(request)
    if payload is None:
        return JSONResponse({"feil": "ugyldig JSON"}, status_code=400)
    raw = payload.get("uriar")
    if not isinstance(raw, list):
        return JSONResponse({"feil": "uriar må vera ei liste"}, status_code=400)

    enriched, book_records = await enrich.enrich([u for u in raw if isinstance(u, str)])
    return JSONResponse(
        {"innslag": enriched, "boker": book_records},
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/samling")
async def api_samling(request: Request) -> Response:
    """In: one followed actor's URI and a page number. Out: that page, as cards.

    This is the endpoint the feed is built on: the browser reads its own follow
    list, keeps the accounts on BookWyrm instances, and walks their outboxes.
    Fifteen posts per request instead of one (ADR 0008).

    An actor URI says whose reading somebody is following, so it is treated
    exactly like a post URI: no log line here, and uvicorn's access log is off in
    the Dockerfile CMD (ADR 0003). The page number is an integer, and the URL we
    fetch is built from the actor's own outbox — never handed to us.
    """
    payload = await _json_body(request)
    if payload is None:
        return JSONResponse({"feil": "ugyldig JSON"}, status_code=400)
    actor = payload.get("aktor")
    if not isinstance(actor, str) or not actor:
        return JSONResponse({"feil": "aktor må vera ein URI"}, status_code=400)
    page = payload.get("side", 1)
    # `bool` is an `int` in Python, and `True` would page an outbox.
    if isinstance(page, bool) or not isinstance(page, int):
        return JSONResponse({"feil": "side må vera eit heiltal"}, status_code=400)
    if not 1 <= page <= config.MAX_OUTBOX_PAGE:
        return JSONResponse({"feil": "side er utanfor rekkjevidde"}, status_code=400)

    try:
        collected = await outbox.collect(actor, page)
    except outbox.OutboxError as refusal:
        return JSONResponse({"feil": refusal.reason}, status_code=400)
    return JSONResponse(collected, headers={"Cache-Control": "no-store"})


@app.post("/api/boker")
async def api_boker(request: Request) -> Response:
    """In: book ids. Out: the ones we have.

    `/api/samling` answers before it has fetched the editions a page mentions, so
    the client comes back for them. One request for the whole screen rather than
    one per card — and, unlike a 404 per unresolved id, this says "not yet"
    without filling the reader's console with failed requests.
    """
    payload = await _json_body(request)
    if payload is None:
        return JSONResponse({"feil": "ugyldig JSON"}, status_code=400)
    raw = payload.get("ider")
    if not isinstance(raw, list):
        return JSONResponse({"feil": "ider må vera ei liste"}, status_code=400)

    found: dict[str, Any] = {}
    for identifier in raw[: config.MAX_BOOK_IDS_PER_REQUEST]:
        if not isinstance(identifier, str):
            continue
        safe = _safe_id(identifier)
        if not safe or safe in found:
            continue
        record = db.get_book(safe)
        if record:
            found[safe] = books.public_book(record)
    return JSONResponse(
        {"boker": found},
        # Whether an edition exists yet changes minute to minute while a sweep is
        # running, so this must not be cached.
        headers={"Cache-Control": "no-store"},
    )


@app.api_route("/api/bok/{book_id}", methods=["GET", "HEAD"])
async def api_bok(book_id: str) -> Response:
    record = db.get_book(_safe_id(book_id))
    if record is None:
        return JSONResponse({"feil": "ukjend bok"}, status_code=404)
    return JSONResponse(
        books.public_book(record),
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.api_route("/omslag/{book_id}", methods=["GET", "HEAD"])
async def omslag(book_id: str) -> Response:
    record = db.get_book(_safe_id(book_id))
    if record is None or not record["cover_file"]:
        return Response("not found", status_code=404)
    path = config.COVER_DIR / record["cover_file"]
    if not path.is_file():
        return Response("not found", status_code=404)
    # Covers are always re-encoded to JPEG on ingest, so the type is pinned here
    # rather than sniffed — combined with nosniff, that is what stops a cover
    # from ever being interpreted as script (§9.4).
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _safe_id(value: str) -> str:
    return "".join(c for c in value if c in "0123456789abcdef")[:20]


async def _json_body(request: Request) -> dict[str, Any] | None:
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > 64 * 1024:
        return None
    try:
        payload = await request.json()
    except (ValueError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


# ── the client ───────────────────────────────────────────────────────────────

@app.api_route("/assets/{filename:path}", methods=["GET", "HEAD"])
async def assets(filename: str) -> Response:
    """Vite's build output: content-hashed, so immutable is truthful."""
    if "/" in filename or ".." in filename or filename.startswith("."):
        return Response("not found", status_code=404)
    path = shell.DIST / "assets" / filename
    if not path.is_file():
        return Response("not found", status_code=404)
    media_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(
        path,
        media_type=media_type or "application/octet-stream",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


# Root-level files Vite copies out of client/public. An explicit allowlist
# rather than "serve anything in dist": the catch-all below must not become a
# way to read arbitrary files out of the image.
ROOT_FILES = {
    "favicon.ico": "image/x-icon",
    "favicon.svg": "image/svg+xml",
    "apple-touch-icon.png": "image/png",
    "icon-192.png": "image/png",
    "icon-512.png": "image/png",
    "site.webmanifest": "application/manifest+json",
}


@app.api_route("/{filename}", methods=["GET", "HEAD"], include_in_schema=False)
async def root_file(filename: str, request: Request) -> Response:
    media_type = ROOT_FILES.get(filename)
    if media_type is None:
        return await spa(filename, request)
    path = shell.DIST / filename
    if not path.is_file():
        return Response("not found", status_code=404)
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=604800"},
    )


@app.api_route("/{path:path}", methods=["GET", "HEAD"])
async def spa(path: str, request: Request) -> Response:
    route = "/" + path.strip("/")
    if route == "/":
        route = "/"
    if route not in SPA_ROUTES and not route.startswith(SPA_PREFIXES):
        return Response("not found", status_code=404)
    if _shell is None or not _shell.available:
        return HTMLResponse(
            "<h1>Lesesalen</h1><p>The client bundle is not built. "
            "Run <code>make client</code> and commit <code>client/dist</code>.</p>",
            status_code=503,
        )

    lang = _language_for(request)
    # The shell is static — built assets plus git-derived dates — so a
    # git-derived Last-Modified (+ 304) is truthful here. It would NOT be if
    # this response ever carried feed content: that is all rendered client-side
    # from the reader's own instance, which is precisely why it can stay.
    modified = _modified_datetime()
    last_modified = format_datetime(modified, usegmt=True)
    if_modified_since = request.headers.get("if-modified-since")
    if if_modified_since:
        with contextlib.suppress(TypeError, ValueError):
            if parsedate_to_datetime(if_modified_since) >= modified.replace(microsecond=0):
                return Response(status_code=304, headers={"Last-Modified": last_modified})

    return HTMLResponse(
        _shell.render(route, lang),
        headers={
            "Last-Modified": last_modified,
            "Cache-Control": "no-cache",
            "Vary": "Accept-Language",
            "Content-Language": lang,
        },
    )


def _language_for(request: Request) -> str:
    """`?sprak=` wins over Accept-Language, so a shared link keeps its language.

    The reader's stored preference lives in localStorage and is applied by the
    client; this only decides what the first paint and `<html lang>` say.
    """
    override = request.query_params.get("sprak", "").strip().lower()
    if override in {"nn", "en"}:
        return override
    return shell.negotiate_language(request.headers.get("accept-language"))


def _modified_datetime() -> datetime:
    """The site's git-derived modified time, as UTC.

    git stamps commits with the committer's local offset (`+02:00` here), and
    `format_datetime(usegmt=True)` refuses anything that is not UTC — so the
    conversion is required, not cosmetic.
    """
    try:
        parsed = datetime.fromisoformat(shell.DATES["modified"])
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
