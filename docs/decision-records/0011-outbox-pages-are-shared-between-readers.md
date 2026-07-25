# 0011 — Outbox pages are cached in memory and shared between readers

- **Status:** Accepted
- **Date:** 2026-07-25
- **Contributors:** Markus (asked & decided: yes to a short-lived shared page
  cache) + Claude (proposed it, implemented)
- **Topics:** performance, privacy, caching, activitypub

## Context

The feed is a sweep over the outboxes of the accounts a reader follows (ADR 0008).
Popular BookWyrm accounts are followed by more than one reader, and until now each
reader's sweep made that account's instance serve the same page again. We are a
guest on those servers, and `netfetch` paces us at one request per domain per
second precisely because we take that seriously — so making the same request twice
is both slow for the second reader and rude to the origin.

Individual *posts* were already shared: `enrich._cache` is keyed by post URI, so
the parse was never repeated. The page fetch was.

The reason not to do this is the reason every cache here is careful: the keys name
actors somebody follows, and the values are other people's posts. ADR 0005 draws
the line at "a cache that spares BookWyrm repeat fetches" versus "a corpus", and
says the difference *is* how long rows live and whether they survive a restart.

## Decision

**Outbox pages are cached in a size-capped, TTL'd, in-memory LRU, keyed by outbox
URL and page number, and shared between readers.**

- Ten minutes by default (`PAGE_CACHE_TTL`), 400 pages (`PAGE_CACHE_SIZE`).
- Memory only. A restart empties it, like every other post-shaped cache here.
- Short deliberately: a shelf gains posts and the feed should notice. This is not
  a store, it is a coalescing window for concurrent readers.
- The same reasoning already covers the actor cache (`_actors`, six hours), which
  holds an actor's outbox URL and item count — infrastructure about a person
  rather than their posts, but keyed by actor URI, so also memory only.

This does put assembled pages of other people's posts in memory where before there
were only individually parsed posts. That is a different shape of the same data
for a shorter time than the enrichment cache's hour, and it is recorded here
rather than left implicit.

## Consequences

- A second reader following the same account gets that page in **5 ms** instead of
  **3.5 s**, and the origin instance serves it once instead of twice.
- Memory: 400 pages at roughly 23 kB of raw `orderedItems` each is about 9 MB
  worst case, on a box with 3.7 GB and a `mem_limit` on this service. Fine, but it
  is the reason the cap is a count and not unbounded.
- A post deleted at the origin can be served for up to ten minutes after. The
  browser's own collection already has a much longer version of this problem
  (ADR 0009), so the page cache is not the binding constraint.
- **Test isolation depends on remembering it exists.** It is module-level state,
  so `tests/test_outbox.py` clears `outbox._pages` in its fixture alongside
  `_actors` and `enrich._cache`. Forgetting one lets a previous test's fetch
  satisfy the next one's, and the `fetched` assertions — which are how most of the
  security guards in that file are observed at all — quietly stop meaning
  anything. This is not hypothetical; it happened while writing this change.
