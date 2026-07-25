# 0010 — A card renders before its edition is fetched, from the cover attachment's name

- **Status:** Accepted
- **Date:** 2026-07-25
- **Contributors:** Markus (reported that the feed took a long time to fill and
  that every timestamp read "57 yr ago"; asked & decided: text first and let the
  cover follow, rather than hotlinking covers from the origin) + Claude (found the
  attachment-name field, diagnosed the date bug, implemented)
- **Topics:** performance, activitypub, bookwyrm, privacy, incident

## Context

Two problems, one cause: the outbox feed needs data the timeline feed used to get
somewhere else, and nobody had gone looking for where the outbox keeps it.

**The slow part.** `/api/samling` awaited `books.ensure_book()` for every post on
a page before answering. For a page of fifteen posts mentioning eight editions
nobody had fetched before, that is an Edition fetch, author fetches, a cover
download, a Pillow re-encode and a blurhash — sometimes with an Open Library
fallback — all at one request per origin domain per second. Measured: **23.4 s**
for one page. The reader stared at a progress line while the *only* thing being
waited on was bibliographic detail.

**The broken part.** Every card claimed to be from 1969. `enrich.parse_object()`
never extracted the ActivityPub `published` field, because the timeline feed read
the date off the Mastodon status and this function had never needed it. The
outbox feed has no other source, so `created_at` was null, `Date.parse` returned
`NaN`, and `formatAge` rendered the epoch. Worse and less visibly: `sortByDate`
compares those same `NaN`s, so **the feed was not in date order at all** — it
just looked plausible because outbox pages arrive newest-first.

Then the useful discovery. BookWyrm names a post's cover attachment after the
edition it belongs to:

```json
"attachment": [{
  "type": "Document",
  "url": "https://…/covers/2346620-c8c4….jpg",
  "name": "Matt Dinniman: This Inevitable Ruin (Hardcover, 2026, Michael Joseph Ltd)"
}]
```

Author, title, format and year — in the page we had already fetched. Measured
across 60 real items from bookwyrm.social: **98%** carry one, and **100%** carry
`published`. `mmsge/bokhylla` had already worked this out and parses the same
string in `lib/parse.js` (`parseEditionName`).

## Decision

**A card is assembled from the outbox page alone. The edition is fetched after
that page has been served.**

- `enrich.parse_object()` returns `publisert` (the validated origin `published`)
  and `bok_kladd` — author, title, format, year, read off the attachment name.
  An unparseable date becomes `None`, never a bad string: `Date.parse` fails
  silently and 1970 is worse than nothing.
- `/api/samling` computes the book id with `books.book_id()`, which is a hash of
  the edition URL and needs no fetch. It returns editions already on disk, and
  spawns resolution of the rest **behind the response**.
- The client renders `bok_kladd` as a draft book (`utkast: true`), then swaps in
  the real record via `POST /api/boker` — one batched request for a screenful,
  a few spaced attempts, then it stops caring. A card with author and title and
  no cover is a perfectly readable card.
- **Covers stay proxied through `/omslag`.** Hotlinking `attachment[].url` would
  be faster still and was considered and rejected: it puts the reader's IP on a
  CDN they never chose, which is exactly what ADR 0004 and the privacy page
  promise it will not. Text first, cover follows.

The spawned resolution is not a background job in the ADR 0008 sense. It is the
tail of a request a present reader made, bounded by `EDITION_CONCURRENCY`, and it
fetches only editions that reader's own page mentioned.

## Consequences

Measured against live `bookwyrm.social`, cold database:

| | before | after |
|---|---|---|
| `/api/samling` page 1, nothing cached | 23.4 s | **3.8 s** |
| the same page for a second reader | 3.5 s | **5 ms** |
| first card painted in the browser | ~23 s | **3.9 s** |

- **Covers arrive a beat late on a cold shelf**, by design. The box reserves the
  cover space so the card does not jump.
- **The 2% without an attachment name** fall back to the previous behaviour: the
  card waits for its edition, or shows the "unknown book" line until one arrives.
- **The trap.** `_parse_item` in `app/outbox.py` is deliberately synchronous and
  fetch-free, and `collect()` deliberately does not await editions. Making either
  of them `await books.ensure_book(...)` again reads as a tidy-up — the function
  is already async, the data would be complete — and silently restores the 23 s.
  `tests/test_outbox.py::test_a_card_is_complete_before_its_edition_is_fetched`
  pins the draft; nothing can pin "and it was fast", so this paragraph has to.
- **The other trap.** `publisert` is the client's only source of date and sort
  order. Anything that drops it from the enrichment dict silently returns the
  feed to random order and 1970, with no error anywhere.
  `test_every_card_carries_the_origins_publication_time` guards it.
- IndexedDB is at `VERSION = 2`: rows written before this record have no
  `publisert` and cannot be repaired locally, so the upgrade drops them and the
  next sweep refetches.
