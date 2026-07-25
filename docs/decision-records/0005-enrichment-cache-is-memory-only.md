# 0005 — Post enrichment lives in memory only, and never on disk

- **Status:** Accepted
- **Date:** 2026-07-25
- **Contributors:** Claude (agent decision — no human input on the technical
  choice)
- **Topics:** privacy, caching, storage

## Context

Enriching a post costs one or more HTTPS round-trips to somebody else's server.
The obvious optimisation is to persist the result: SQLite is already there, the
data is small, and a restart currently throws away work.

That optimisation would also quietly convert Lesesalen from a client into an
archive of what people are reading — which is the thing ADR 0002 says it is not.
The difference between "a cache that spares BookWyrm repeat fetches" and "a
corpus of other people's book posts" is entirely a matter of how long the rows
live and whether they survive a restart.

## Decision

**Post enrichment lives in a size-capped, TTL'd, in-memory LRU
(`app/cache.py`), roughly one hour, and is never written to disk.**

- A restart empties it. That is correct behaviour, not a limitation to fix.
- Negative results are cached too — a post that is not a book post is the common
  case, and re-fetching it on every scroll would be rude to the origin — using
  the same TTL and the same volatility (`NOT_A_BOOK_POST`).
- `cache_stats()` returns sizes only, never keys. The keys are post URIs.
- What *is* persisted, in SQLite, is deliberately limited to two things that are
  not about a person: instance nodeinfo (infrastructure metadata) and
  bibliographic data plus cover files (a book edition is not anyone's personal
  information).

## Consequences

- After a deploy the first readers pay for re-enrichment. With a per-domain rate
  limit of one request per second this is noticeable but not harmful, and it is
  the price of the guarantee.
- The cache is shared between all readers, which is also a privacy property:
  requests are not attributable to a person.
- `LESESALEN_ENRICH_CACHE_TTL` and `_SIZE` tune the cache. Raising the TTL to
  something like a week would technically work and would quietly turn this into
  the corpus this record exists to prevent. If that is ever wanted, it needs a
  new ADR, not an env var change.
- **The tell that this decision is being undone:** a `status` or `post` table in
  `app/db.py`. There is a note at the top of that module saying so.
