"""robots.txt, honoured on the scrape path.

The ActivityPub re-fetch is an API read of an object the instance published for
federation, and robots.txt has never governed that. The Open Graph fallback is
different: it asks for the human-facing HTML page, which is exactly what
robots.txt is about. So the scrape path checks, and the AP path does not.

Unreachable robots.txt follows the usual convention: 4xx means "no rules, go
ahead", anything else (5xx, transport failure) means "assume not".
"""
from __future__ import annotations

from urllib.robotparser import RobotFileParser
from urllib.parse import urlsplit

from . import netfetch
from .cache import TTLCache

USER_AGENT_TOKEN = "Lesesalen"

_cache: TTLCache[RobotFileParser | None] = TTLCache(max_size=500, ttl=24 * 3600)


async def _load(host: str) -> RobotFileParser | None:
    """None means "we could not establish the rules" — callers must not scrape."""
    cached = _cache.get(host)
    if cached is not None:
        return cached
    parser = RobotFileParser()
    try:
        fetched = await netfetch.fetch(
            f"https://{host}/robots.txt",
            allowed_hosts={host},
            accept="text/plain",
            max_bytes=256 * 1024,
            attempts=1,
        )
        parser.parse(fetched.body.decode("utf-8", "replace").splitlines())
    except netfetch.StatusError as exc:
        if 400 <= exc.status < 500:
            parser.parse([])  # no rules published: everything is allowed
        else:
            return None
    except netfetch.FetchError:
        return None
    _cache.put(host, parser)
    return parser


async def may_scrape(url: str) -> bool:
    host = netfetch.normalise_domain(urlsplit(url).hostname or "")
    if not host:
        return False
    parser = await _load(host)
    if parser is None:
        return False
    return parser.can_fetch(USER_AGENT_TOKEN, url)
