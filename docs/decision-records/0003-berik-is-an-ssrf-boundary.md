# 0003 — `/api/berik` is an SSRF boundary, and every guard on it is load-bearing

- **Status:** Accepted
- **Date:** 2026-07-25
- **Contributors:** Claude (agent decision — no human input on the technical
  choice; the brief specified the guards as non-negotiable, and this record
  captures *why* each one is there and what DNS pinning buys)
- **Topics:** security, ssrf, privacy, logging, activitypub

## Context

`/api/berik` takes URLs from anonymous callers and fetches them server-side.
That is the definition of a server-side request forgery primitive. Without
constraints it is an open proxy sitting inside the box's Docker network, where
`172.18.0.1` is the bridge gateway, every other service is reachable on
`172.18.0.1:40xx`, and `169.254.169.254` is one request away from cloud
metadata.

It is also a privacy boundary in the other direction: the URIs passing through
it say what a particular person is reading, right now.

## Decision

Every guard in `app/netfetch.py` is load-bearing. Removing any one of them
re-opens the hole.

1. **Allowlist first.** A host must already be nodeinfo-confirmed BookWyrm
   before any fetch. `instances.is_confirmed_bookwyrm()` is deliberately
   synchronous and cache-only: `/api/berik` must not be able to *induce* a probe
   of a host it was not already told about via `/api/instansar`. No allowlist
   entry, no fetch.
2. **https only, default port only, no IP literals in the URL.**
3. **Address filtering with DNS pinning.** We resolve the hostname ourselves and
   reject private, loopback, link-local, CGNAT, multicast, reserved and
   metadata addresses — refusing the *whole name* if any of its addresses is
   non-public, because a name answering with both is a rebinding attempt rather
   than a service. Then we connect **to the address we validated**, passing the
   real hostname as SNI and `Host` so TLS verification is unchanged. Resolving
   and then handing the name to the HTTP client would leave a rebinding window
   between the check and the connection; pinning closes it.
4. **Manual redirect following**, capped, with the allowlist, scheme and
   addresses re-checked at every hop. A `302` to `127.0.0.1` is the oldest trick
   there is.
5. **Size caps enforced while streaming, and short timeouts**, so a hostile or
   broken origin cannot exhaust a 384 MB container.
6. **Per-IP token bucket** on the API, keyed on the *last* `X-Forwarded-For`
   entry — Caddy appends the real peer, so taking the first entry (the usual
   reflex) would let anyone rotate their apparent identity per request.
7. **No request logging.** The URIs reveal what someone is reading. They pass
   through memory and leave no trace: nothing in this codebase logs them, and
   uvicorn's access log is disabled in the Dockerfile `CMD` for the same reason.
   Caddy still logs the *path* `/api/berik`, which carries no URIs — the bodies
   are never written anywhere.

Two bounded exceptions, both deliberate and both narrower than they look:

- **Cover images** are fetched from whatever host the instance's own
  ActivityPub document names — BookWyrm keeps covers on object storage
  (`bookwyrm-social.sfo3.digitaloceanspaces.com`), not on the instance domain,
  so requiring the instance host would mean no covers anywhere. The URL is not
  caller-supplied: it comes out of a document we already fetched from a
  confirmed BookWyrm host, so the allowlist did its job one step earlier. Every
  other guard still applies, plus raster-only validation and a full re-encode
  (ADR 0004).
- **A forward proxy disables pinning.** If `HTTPS_PROXY` is set, the proxy does
  the connecting and a `CONNECT` to a raw IP is refused, so we dial by hostname
  instead. This weakens the rebinding defence to advisory. It is acceptable
  because the allowlist remains the primary control and the box has direct
  outbound access with no proxy — the pinned path is what actually ships.

## Consequences

- `tests/test_security.py` pins the address and URL rules. If one of those tests
  starts failing, something in the security model has been undone rather than
  refactored — do not adjust the test to match the code.
- Setting `LESESALEN_ALLOW_PRIVATE_ADDRESSES=1` turns the address filter off. It
  exists for local testing and must never be set on the box.
- A BookWyrm instance behind a hostname that resolves to a private address (an
  intranet instance) is unreachable by design. That is the correct trade.
