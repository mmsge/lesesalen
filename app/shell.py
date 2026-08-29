"""The HTML shell: Vite's built index.html plus the metadata the box requires.

The client is a single-page app, so there is one built `index.html`. Rather than
letting it ship bare, the server injects into its `<head>` at request time:

* the git-derived created/modified metadata every site on the box carries
  (naustet-server ADR 0015) — meta date/last-modified, article:published_time /
  article:modified_time, and the JSON-LD WebSite node;
* per-route title, description, canonical and Open Graph tags for the three
  public pages, so an unfurl or a crawler gets something true rather than the
  generic shell;
* `<html lang>` matching the language actually being served;
* preload hints for the self-hosted fonts, whose filenames are content-hashed
  by Vite and therefore only knowable at boot.

If `client/dist` is missing the app still boots and serves the API — only the UI
is gone — which keeps a broken client build from taking the service down.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
from datetime import datetime, timezone
from typing import Any

from . import config

DIST = pathlib.Path(__file__).resolve().parent.parent / "client" / "dist"
INDEX = DIST / "index.html"

# Public routes, and what each should say when something that is not a browser
# asks. Everything else is either the reader's own feed (never crawlable, never
# unfurled) or the API.
ROUTES: dict[str, dict[str, dict[str, str]]] = {
    "/": {
        "nn": {
            "title": "Lesesalen — berre bokinnlegga",
            "description": (
                "Ein Mastodon-klient som viser deg berre bokinnlegga frå BookWyrm: "
                "meldingar, terningkast, kommentarar, sitat og lesestatusar."
            ),
        },
        "en": {
            "title": "Lesesalen — only the book posts",
            "description": (
                "A Mastodon client that shows you only the BookWyrm book posts: "
                "reviews, ratings, comments, quotations and reading statuses."
            ),
        },
    },
    "/om": {
        "nn": {
            "title": "Om Lesesalen",
            "description": "Kva Lesesalen er, kva han ikkje er, og kvifor det finst ein tenar.",
        },
        "en": {
            "title": "About Lesesalen",
            "description": "What Lesesalen is, what it deliberately is not, and why a server exists.",
        },
    },
    "/personvern": {
        "nn": {
            "title": "Personvern — Lesesalen",
            "description": "Ingen brukarkontoar, ingen token, ingen lesehistorikk. Kva som faktisk vert lagra.",
        },
        "en": {
            "title": "Privacy — Lesesalen",
            "description": "No accounts, no tokens, no reading history. What is actually stored.",
        },
    },
}

_BOOT_ISO = datetime.now(timezone.utc).isoformat()


def page_dates() -> dict[str, str]:
    """Site created/modified from git history.

    Written by scripts/generate-page-dates.sh on the checkout at deploy — the
    image has no .git, and the box has no Python outside containers. Falls back
    to boot time when the file is absent (a bare `docker build`).
    """
    path = pathlib.Path(__file__).resolve().parent.parent / "page-dates.json"
    try:
        data = json.loads(path.read_text())
        return {
            "created": str(data["created"]),
            "modified": str(data["modified"]),
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {"created": _BOOT_ISO, "modified": _BOOT_ISO}


DATES = page_dates()


def _font_preloads() -> str:
    """Preload the two faces every page actually paints with.

    Vite content-hashes the woff2 filenames, so this can only be resolved at
    boot. Only the upright latin faces are preloaded: preloading is
    unconditional, so listing latin-ext and italic here would download them for
    every reader and undo the `unicode-range` subsetting in fonts.css.
    """
    assets = DIST / "assets"
    if not assets.is_dir():
        return ""
    return "".join(
        f'<link rel="preload" href="/assets/{html.escape(font.name)}" as="font" '
        'type="font/woff2" crossorigin>'
        for font in sorted(assets.glob("*-latin-wght-normal-*.woff2"))
    )


def _jsonld(route: str, meta: dict[str, str]) -> str:
    node = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Lesesalen",
        "url": f"{config.BASE_URL}/",
        "description": meta["description"],
        "inLanguage": ["nn", "en"],
        "dateCreated": DATES["created"],
        "datePublished": DATES["created"],
        "dateModified": DATES["modified"],
    }
    if route != "/":
        node = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": meta["title"],
            "url": f"{config.BASE_URL}{route}",
            "description": meta["description"],
            "isPartOf": {"@type": "WebSite", "name": "Lesesalen", "url": f"{config.BASE_URL}/"},
            "dateCreated": DATES["created"],
            "datePublished": DATES["created"],
            "dateModified": DATES["modified"],
        }
    # `</` is escaped so the payload can never close the script element early.
    return json.dumps(node, ensure_ascii=False).replace("<", "\\u003c")


def head_for(route: str, lang: str) -> str:
    public = route in ROUTES
    entry = ROUTES.get(route, ROUTES["/"])
    meta = entry.get(lang, entry["nn"])
    title = html.escape(meta["title"])
    description = html.escape(meta["description"])
    canonical = html.escape(f"{config.BASE_URL}{route}")
    return "".join(
        [
            f"<title>{title}</title>",
            f'<meta name="description" content="{description}">',
            f'<link rel="canonical" href="{canonical}">',
            f'<meta name="date" content="{html.escape(DATES["created"])}">',
            f'<meta name="last-modified" content="{html.escape(DATES["modified"])}">',
            f'<meta property="article:published_time" content="{html.escape(DATES["created"])}">',
            f'<meta property="article:modified_time" content="{html.escape(DATES["modified"])}">',
            '<meta property="og:type" content="website">',
            '<meta property="og:site_name" content="Lesesalen">',
            f'<meta property="og:title" content="{title}">',
            f'<meta property="og:description" content="{description}">',
            f'<meta property="og:url" content="{canonical}">',
            f'<meta property="og:locale" content="{"nn_NO" if lang == "nn" else "en_GB"}">',
            '<meta name="twitter:card" content="summary">',
            f'<meta name="twitter:title" content="{title}">',
            f'<meta name="twitter:description" content="{description}">',
            '<link rel="alternate" hreflang="nn" href="' + html.escape(f"{config.BASE_URL}{route}") + '">',
            '<link rel="alternate" hreflang="en" href="' + html.escape(f"{config.BASE_URL}{route}") + '">',
            _font_preloads(),
            # The feed, settings and author views are one reader's own view of
            # their own timeline. There is nothing there for an index.
            "" if public else '<meta name="robots" content="noindex, nofollow">',
            f'<script type="application/ld+json">{_jsonld(route, meta)}</script>',
        ]
    )


_LANG_RE = re.compile(r'<html[^>]*\blang="[^"]*"', re.I)


class Shell:
    """Holds the built index.html and stamps it per request."""

    def __init__(self) -> None:
        self.available = INDEX.is_file()
        self._template = INDEX.read_text(encoding="utf-8") if self.available else ""

    def render(self, route: str, lang: str) -> str:
        if not self.available:
            raise FileNotFoundError(INDEX)
        page = self._template
        if _LANG_RE.search(page):
            page = _LANG_RE.sub(f'<html lang="{lang}"', page, count=1)
        else:
            page = page.replace("<html", f'<html lang="{lang}"', 1)
        head = head_for(route, lang)
        if "</head>" in page:
            return page.replace("</head>", f"{head}</head>", 1)
        return head + page


def negotiate_language(accept_language: str | None) -> str:
    """Nynorsk default, English second — the only two catalogues that exist."""
    if not accept_language:
        return "nn"
    best_lang, best_q = "nn", -1.0
    for part in accept_language.split(",")[:12]:
        piece = part.strip()
        if not piece:
            continue
        tag, _, params = piece.partition(";")
        quality = 1.0
        if params.strip().startswith("q="):
            try:
                quality = float(params.strip()[2:])
            except ValueError:
                quality = 1.0
        tag = tag.strip().lower()
        if tag.startswith(("nn", "no", "nb")):
            candidate = "nn"
        elif tag.startswith("en"):
            candidate = "en"
        else:
            continue
        if quality > best_q:
            best_lang, best_q = candidate, quality
    return best_lang if best_q >= 0 else "nn"


def static_file(name: str) -> dict[str, Any] | None:
    """robots.txt / sitemap.xml, with __LASTMOD__ stamped."""
    path = pathlib.Path(__file__).resolve().parent.parent / name
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return {"body": body.replace("__LASTMOD__", DATES["modified"])}
