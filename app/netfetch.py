"""Outbound HTTP: the only place in lesesalen that talks to the open internet.

`/api/berik` takes URLs from anonymous callers and fetches them. Without the
guards below that endpoint is an open proxy and an SSRF hole into the box, so
every rule here is load-bearing (ADR 0003):

* **https only**, default port only, no URL-literal IP addresses.
* **Allowlist first.** A host must already be nodeinfo-confirmed BookWyrm (or one
  of the two Open Library hosts the fallback chain needs). No entry, no fetch.
* **Address filtering with DNS pinning.** We resolve the hostname ourselves,
  reject private / loopback / link-local / CGNAT / metadata addresses, and then
  connect *to the address we validated* — passing the real hostname as SNI and
  Host so TLS verification is still against the real name. Resolving and then
  handing the name to the HTTP client would leave a DNS-rebinding window between
  the check and the connection; pinning closes it.
* **Redirects are followed manually**, capped, and re-validated at every hop —
  allowlist, scheme and addresses all re-checked. A 302 to 127.0.0.1 is the
  oldest trick there is.
* **Size caps and short timeouts**, enforced while streaming, so a hostile or
  broken origin cannot exhaust a 384 MB container.
* **Per-domain politeness**, one request per second, honouring 429/Retry-After
  with backoff and jitter. We are a guest on other people's servers.

Nothing here logs a URL. The URIs passing through describe what somebody is
reading (ADR 0003).
"""
from __future__ import annotations

import asyncio
import ipaddress
import os
import random
import re
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

import httpx

from . import config

# Extra networks ipaddress does not flag as private on every Python version, plus
# the cloud metadata endpoints that are the classic SSRF payoff.
_EXTRA_BLOCKED = [
    ipaddress.ip_network("100.64.0.0/10"),      # CGNAT
    ipaddress.ip_network("192.0.0.0/24"),       # IETF protocol assignments
    ipaddress.ip_network("198.18.0.0/15"),      # benchmarking
    ipaddress.ip_network("169.254.0.0/16"),     # link-local incl. 169.254.169.254
    ipaddress.ip_network("fd00::/8"),           # unique local
    ipaddress.ip_network("fe80::/10"),          # link-local v6
]

_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


class FetchError(Exception):
    """Any outbound fetch that did not produce a usable response."""


class BlockedError(FetchError):
    """The request was refused by policy before or during the fetch."""


class TooLargeError(FetchError):
    """The response exceeded its size cap."""


class StatusError(FetchError):
    """The origin answered, but with an error status."""

    def __init__(self, status: int) -> None:
        super().__init__(f"status {status}")
        self.status = status


@dataclass(slots=True)
class Fetched:
    url: str
    status: int
    content_type: str
    body: bytes


# ── hostnames and addresses ──────────────────────────────────────────────────

def normalise_domain(raw: str) -> str | None:
    """Return a clean lowercase hostname, or None if it is not one.

    Rejects IP literals, ports, userinfo, paths and anything that is not a
    plausible DNS name. Callers pass these straight into an allowlist lookup,
    so being strict here is cheap insurance.
    """
    if not raw or not isinstance(raw, str):
        return None
    host = raw.strip().lower()
    if "://" in host:
        host = urlsplit(host).hostname or ""
    host = host.strip("/").split("/")[0].split("@")[-1]
    if host.startswith("[") or ":" in host:  # IPv6 literal or host:port
        return None
    host = host.rstrip(".")
    if not host or len(host) > 253:
        return None
    try:
        host = host.encode("idna").decode("ascii").lower()
    except (UnicodeError, ValueError):
        return None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return None  # bare IP address is never an instance domain
    if not _HOSTNAME_RE.match(host):
        return None
    return host


def address_is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True only for addresses we are willing to open a socket to."""
    if getattr(ip, "ipv4_mapped", None) is not None:
        ip = ip.ipv4_mapped  # type: ignore[assignment]
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False
    return not any(ip in net for net in _EXTRA_BLOCKED)


async def resolve_public_addresses(host: str) -> list[str]:
    """Resolve `host` and return its addresses, refusing if *any* is non-public.

    Refusing the whole name — rather than filtering to the public subset — is
    deliberate: a name that answers with both a public and a private address is
    a rebinding attempt, not a service we want to talk to.
    """
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchError("dns") from exc
    addresses: list[str] = []
    for family, _type, _proto, _canon, sockaddr in infos:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        addr = sockaddr[0]
        try:
            parsed = ipaddress.ip_address(addr.split("%")[0])
        except ValueError:
            continue
        if not config.ALLOW_PRIVATE_ADDRESSES and not address_is_public(parsed):
            raise BlockedError("non-public address")
        addresses.append(addr.split("%")[0])
    if not addresses:
        raise FetchError("dns")
    # De-duplicate, keeping order (getaddrinfo already sorts by preference).
    seen: set[str] = set()
    return [a for a in addresses if not (a in seen or seen.add(a))]


# ── politeness ───────────────────────────────────────────────────────────────

class DomainThrottle:
    """One request per domain per `interval`, plus a 429-driven cooldown."""

    def __init__(self, interval: float) -> None:
        self._interval = interval
        self._locks: dict[str, asyncio.Lock] = {}
        self._last: dict[str, float] = {}
        self._cooldown: dict[str, float] = {}

    def _lock(self, domain: str) -> asyncio.Lock:
        lock = self._locks.get(domain)
        if lock is None:
            lock = self._locks[domain] = asyncio.Lock()
        return lock

    def cooling_down(self, domain: str) -> bool:
        return time.monotonic() < self._cooldown.get(domain, 0.0)

    def back_off(self, domain: str, retry_after: float | None) -> None:
        seconds = retry_after if retry_after is not None else 60.0
        seconds = min(max(seconds, 1.0), 900.0)
        seconds += random.uniform(0, min(seconds, 5.0))  # jitter, so we don't sync up
        self._cooldown[domain] = time.monotonic() + seconds

    def acquire(self, domain: str) -> "_ThrottleSlot":
        """`async with throttle.acquire(domain):` — serialises and paces a domain."""
        return _ThrottleSlot(self, domain)

    async def _wait_turn(self, domain: str) -> None:
        elapsed = time.monotonic() - self._last.get(domain, 0.0)
        if elapsed < self._interval:
            await asyncio.sleep(self._interval - elapsed)

    def _mark(self, domain: str) -> None:
        self._last[domain] = time.monotonic()


class _ThrottleSlot:
    def __init__(self, throttle: DomainThrottle, domain: str) -> None:
        self._throttle = throttle
        self._domain = domain

    async def __aenter__(self) -> None:
        await self._throttle._lock(self._domain).acquire()
        await self._throttle._wait_turn(self._domain)

    async def __aexit__(self, *_exc) -> None:
        self._throttle._mark(self._domain)
        self._throttle._lock(self._domain).release()


_throttle = DomainThrottle(config.DOMAIN_INTERVAL)


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.strip())
    except ValueError:
        pass
    from email.utils import parsedate_to_datetime

    try:
        from datetime import datetime, timezone

        when = parsedate_to_datetime(value)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return None


# ── the client ───────────────────────────────────────────────────────────────

_client: httpx.AsyncClient | None = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            follow_redirects=False,  # we follow them ourselves, re-validating each hop
            timeout=httpx.Timeout(config.FETCH_TIMEOUT, connect=5.0),
            limits=httpx.Limits(max_connections=16, max_keepalive_connections=8),
            headers={"User-Agent": config.USER_AGENT},
            trust_env=True,
        )
    return _client


async def aclose() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def proxy_configured() -> bool:
    """Is outbound HTTPS going through a forward proxy?

    Pinning and a forward proxy are mutually exclusive: the proxy does the
    connecting, so a CONNECT to a raw IP literal is at best refused and at worst
    reaches a different host than the certificate we would verify. When a proxy
    is configured we therefore dial by hostname and let it resolve.

    That is a real, if narrow, weakening — the address check becomes advisory
    against DNS rebinding rather than binding. It is acceptable because the
    allowlist is the primary control (a host must already be nodeinfo-confirmed
    BookWyrm), and because the box this runs on has direct outbound access with
    no proxy at all, so the pinned path is what actually ships.
    """
    return any(
        os.environ.get(name)
        for name in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy")
    )


def _pinned(url: str, address: str) -> tuple[str, str]:
    """Rewrite `url` to dial a validated IP, returning (url, host_header).

    The connection goes to the address we checked; the Host header and SNI keep
    the real hostname, so certificate verification is unchanged.
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    if proxy_configured():
        return url, host
    literal = f"[{address}]" if ":" in address else address
    return urlunsplit((parts.scheme, literal, parts.path or "/", parts.query, "")), host


def _check_url(url: str, allowed_hosts: frozenset[str] | set[str]) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise BlockedError("scheme")
    host = normalise_domain(parts.hostname or "")
    if host is None:
        raise BlockedError("host")
    if parts.port not in (None, 443):
        raise BlockedError("port")
    if host not in allowed_hosts:
        raise BlockedError("host not allowed")
    return host


_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})


async def fetch(
    url: str,
    *,
    allowed_hosts: frozenset[str] | set[str],
    accept: str,
    max_bytes: int,
    attempts: int = 2,
) -> Fetched:
    """Fetch `url` under every guard in this module's docstring.

    `allowed_hosts` must contain the host of the initial URL *and* the host of
    every redirect target — the caller decides what "allowed" means (usually:
    nodeinfo-confirmed BookWyrm).
    """
    current = url
    for _hop in range(config.MAX_REDIRECTS + 1):
        host = _check_url(current, allowed_hosts)
        if _throttle.cooling_down(host):
            raise BlockedError("cooling down")
        addresses = await resolve_public_addresses(host)

        result = await _send(current, host, addresses, accept, max_bytes, attempts)
        if isinstance(result, Fetched):
            return result
        # A redirect: resolve it against the current URL and go round again, so
        # scheme, allowlist and addresses are all re-checked for the new target.
        current = httpx.URL(current).join(result).__str__()
    raise FetchError("too many redirects")


async def _send(
    url: str,
    host: str,
    addresses: list[str],
    accept: str,
    max_bytes: int,
    attempts: int,
) -> Fetched | str:
    """One hop. Returns a Fetched, or a redirect Location for the caller to vet."""
    last_error: Exception | None = None
    for attempt in range(max(1, attempts)):
        target, host_header = _pinned(url, addresses[attempt % len(addresses)])
        headers = {"Accept": accept, "Host": host_header}
        try:
            async with _throttle.acquire(host):
                async with client().stream(
                    "GET",
                    target,
                    headers=headers,
                    extensions={"sni_hostname": host_header},
                ) as response:
                    if response.status_code in _REDIRECT_CODES:
                        location = response.headers.get("location")
                        await response.aclose()
                        if not location:
                            raise FetchError("redirect without location")
                        return location
                    if response.status_code == 429 or response.status_code >= 500:
                        retry_after = parse_retry_after(response.headers.get("retry-after"))
                        await response.aclose()
                        if response.status_code == 429:
                            _throttle.back_off(host, retry_after)
                            raise BlockedError("rate limited by origin")
                        last_error = StatusError(response.status_code)
                        if attempt + 1 < attempts:
                            await asyncio.sleep(0.5 * (2**attempt) + random.uniform(0, 0.4))
                            continue
                        raise last_error
                    if response.status_code >= 400:
                        status = response.status_code
                        await response.aclose()
                        raise StatusError(status)

                    declared = response.headers.get("content-length")
                    if declared and declared.isdigit() and int(declared) > max_bytes:
                        await response.aclose()
                        raise TooLargeError("content-length")

                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > max_bytes:
                            await response.aclose()
                            raise TooLargeError("body")
                        chunks.append(chunk)

                    return Fetched(
                        url=url,
                        status=response.status_code,
                        content_type=response.headers.get("content-type", ""),
                        body=b"".join(chunks),
                    )
        except (BlockedError, TooLargeError):
            raise
        except (httpx.HTTPError, OSError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                await asyncio.sleep(0.5 * (2**attempt) + random.uniform(0, 0.4))
                continue
            raise FetchError("transport") from exc
    raise FetchError("transport") from last_error
