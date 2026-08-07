# 0015 — `/health` names no upstream instance

- **Status:** Accepted
- **Date:** 2026-08-07
- **Contributors:** Claude (agent decision — no human input on the technical
  choice)
- **Topics:** privacy, observability, health, ops

## Context

Every service on the box now answers `/healthz`, `/version` and `/health`
(hetzner-server ADR 0022). The contract's redaction rules are an allowlist, and
they explicitly *permit* naming public third-party upstreams: `api.met.no` is not
a secret, and naming it is what makes a failing check actionable. The reference
implementation and the box's model service (`padletid`) both do exactly that,
with a per-upstream `age_seconds` since the last success.

Lesesalen cannot copy that, and the reason is not obvious from the contract.

Its upstreams are not a fixed list of public APIs. They are the BookWyrm
instances a *reader* follows — arbitrary, unknown until somebody asks, and
discovered one HTTP request at a time. A check named `upstream:bokwyrm.example`
with an age since last success is therefore a public statement that somebody has
recently been reading an account on that instance. On a small instance that is
close to naming the reader. It is the same leak `/api/berik` is built to avoid
(ADR 0003) and the same corpus ADR 0005 refuses to accumulate, arriving through
the one endpoint whose whole purpose is to be read by strangers.

## Decision

**`/health` publishes a closed set of four check names, and none of them is an
upstream:** `database`, `storage`, `render`, `cache` (the tuple
`main.HEALTH_CHECKS`).

- `database` runs a real query and reports one row count — a bare cardinal, not
  a per-table breakdown, because a breakdown describes the schema.
- `storage` is whether covers can still be written: a status, never the path.
- `render` is whether the committed client bundle is in the image (ADR 0001).
  This one is genuinely invisible to `/healthz`: the process is perfectly alive
  while every page answers 503.
- `cache` reports enrichment cache occupancy as a count. It is the honest proxy
  for upstream health — it moves when origin fetches succeed — and it names
  nobody, exactly as `cache_stats()` was already written to guarantee.

Failure `detail` comes from the contract's fixed vocabulary (`main.DETAIL`) or is
a plain count. Never `str(exc)`: a `sqlite3` message quotes the database path.

## Consequences

- A single sick BookWyrm instance is invisible in `/health`. That is accepted:
  the reader sees it immediately as a card that will not enrich, and a
  server-side view of it cannot be built without recording whose instance it is.
- The four checks are still substantive, so `/health` is not `/healthz` with
  extra steps — the box's contract requires at least one real check and this
  clears that bar without the privacy cost.
- **The tell that this decision is being undone:** an `upstream:` entry in
  `HEALTH_CHECKS`, or any per-domain state kept solely so `/health` can report
  it. Both mean the endpoint has started publishing what people read.
