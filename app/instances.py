"""Which fediverse domains run BookWyrm — the allowlist everything else keys off.

The browser sends bare domain names, never a follow list: it has already read
the timeline and just needs to know which authors are on BookWyrm servers. The
answer is per-domain infrastructure metadata, so one probe serves everybody and
is cached for 30 days.

This is also the gate for `/api/berik`. A host that is not confirmed BookWyrm
here is never fetched, which is what stops that endpoint being an open proxy.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from . import config, db, netfetch

_NODEINFO_RELS = {
    "http://nodeinfo.diaspora.software/ns/schema/2.0",
    "http://nodeinfo.diaspora.software/ns/schema/2.1",
}

# Probes run against arbitrary user-supplied domains, so they are limited and
# serialised — a caller should not be able to turn one request into a portscan.
_probe_semaphore = asyncio.Semaphore(4)
_inflight: dict[str, asyncio.Task] = {}


async def _fetch_json(url: str, host: str) -> Any:
    fetched = await netfetch.fetch(
        url,
        allowed_hosts={host},
        accept="application/json, application/activity+json;q=0.5",
        max_bytes=config.MAX_JSON_BYTES,
    )
    return json.loads(fetched.body.decode("utf-8", "replace"))


async def _probe(domain: str) -> dict[str, Any]:
    """Ask a domain what software it runs, via the nodeinfo well-known."""
    software_name: str | None = None
    software_version: str | None = None
    try:
        index = await _fetch_json(f"https://{domain}/.well-known/nodeinfo", domain)
        href = None
        links = index.get("links") if isinstance(index, dict) else None
        for link in links or []:
            if not isinstance(link, dict):
                continue
            if link.get("rel") in _NODEINFO_RELS and isinstance(link.get("href"), str):
                href = link["href"]  # prefer the highest schema version offered
        if href is None:
            raise netfetch.FetchError("no nodeinfo link")
        # The href must stay on the same host: otherwise a hostile domain could
        # point us at somebody else's server and use us as a probe amplifier.
        document = await _fetch_json(href, domain)
        software = document.get("software") if isinstance(document, dict) else None
        if isinstance(software, dict):
            name = software.get("name")
            version = software.get("version")
            software_name = name.lower().strip() if isinstance(name, str) else None
            software_version = version.strip()[:64] if isinstance(version, str) else None
    except (netfetch.FetchError, ValueError, KeyError, AttributeError, TypeError):
        software_name = None

    is_bookwyrm = software_name == "bookwyrm"
    db.put_instance(domain, software_name, software_version, is_bookwyrm)
    return {
        "domain": domain,
        "software_name": software_name,
        "software_version": software_version,
        "is_bookwyrm": is_bookwyrm,
    }


async def _probe_once(domain: str) -> dict[str, Any]:
    """Probe `domain`, collapsing concurrent callers onto a single request."""
    existing = _inflight.get(domain)
    if existing is not None:
        return await asyncio.shield(existing)

    async def run() -> dict[str, Any]:
        try:
            async with _probe_semaphore:
                return await _probe(domain)
        finally:
            _inflight.pop(domain, None)

    task = asyncio.create_task(run())
    _inflight[domain] = task
    return await asyncio.shield(task)


async def describe(domains: list[str]) -> dict[str, dict[str, Any]]:
    """Return {domain: {...}} for every valid domain given, probing the unknown."""
    wanted: list[str] = []
    for raw in domains[: config.MAX_DOMAINS_PER_REQUEST]:
        normalised = netfetch.normalise_domain(raw)
        if normalised and normalised not in wanted:
            wanted.append(normalised)
    if not wanted:
        return {}

    known = db.get_instances(wanted)
    answers: dict[str, dict[str, Any]] = {}
    to_probe: list[str] = []
    for domain in wanted:
        record = known.get(domain)
        if record is not None and db.instance_is_fresh(record):
            answers[domain] = record
        else:
            to_probe.append(domain)

    if to_probe:
        probed = await asyncio.gather(
            *(_probe_once(domain) for domain in to_probe), return_exceptions=True
        )
        for domain, result in zip(to_probe, probed):
            if isinstance(result, BaseException):
                answers[domain] = {
                    "domain": domain,
                    "software_name": None,
                    "software_version": None,
                    "is_bookwyrm": False,
                }
            else:
                answers[domain] = result
    return answers


def is_confirmed_bookwyrm(domain: str) -> bool:
    """Allowlist check — cache only, never probes.

    Deliberately synchronous and side-effect free: `/api/berik` must not be able
    to induce a fetch to a host it has not already been told about via
    `/api/instansar`. No allowlist entry, no fetch.
    """
    normalised = netfetch.normalise_domain(domain)
    if not normalised:
        return False
    record = db.get_instance(normalised)
    return bool(record and record["is_bookwyrm"])
