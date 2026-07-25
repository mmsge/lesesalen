# 0008 — The feed is the outboxes of the accounts you follow, not your home timeline

- **Status:** Accepted
- **Supersedes:** [0002](0002-a-client-not-a-crawler.md)
- **Date:** 2026-07-25
- **Contributors:** Markus (asked & decided: collect from the outboxes with
  nothing new stored on the server; the collection replaces the home feed rather
  than sitting beside it) + Claude (proposed the outbox route, probed BookWyrm to
  establish it was possible, implemented)
- **Topics:** privacy, architecture, activitypub, bookwyrm, product, performance

## Context

ADR 0002 built the feed on the reader's Mastodon **home timeline**: keep the
statuses whose author is on a BookWyrm instance, re-fetch each one's origin
object through `/api/berik` to recover what Mastodon discarded. It had three
structural problems, and they were not incidental.

1. **Sparseness.** A home timeline is mostly not books, so the first screen was
   thin and `loadMore` paged backwards up to six times hunting for eight book
   posts.
2. **Cost per post.** One post meant one origin fetch, and `netfetch` allows one
   request per origin domain per second as a politeness guarantee. Twenty cards
   was twenty seconds of throttled fetching, shared across every reader of the
   server. ADR 0002 already recorded a version of this: *"the first readers pay
   for re-enrichment … noticeable but not harmful."* At feed scale it was
   harmful.
3. **Only the recent slice.** You saw what your instance happened to have
   delivered. A BookWyrm account with a decade of reviews had a decade of reviews
   you could not reach.

ADR 0002's own answer was an explicit, secondary `gather()` action: walk the
follow list, keep the BookWyrm accounts, ask the reader's instance for each one's
statuses. It worked, and it was slow for exactly reason 2 — one `/api/berik`
fetch per post meant gathering fifteen accounts took minutes.

**Then we checked what a BookWyrm outbox actually serves.** Verified live against
`bookwyrm.social`:

```
GET https://bookwyrm.social/user/mvrkws          Accept: application/activity+json
  → type: Person, bookwyrmUser: true, outbox: …/user/mvrkws/outbox
GET …/user/mvrkws/outbox
  → OrderedCollection, totalItems 1092, last: …?page=73
GET …/user/mvrkws/outbox?page=1
  → 15 orderedItems, newest first
  → id segments: generatednote | comment | review | quotation | status
  → type: Note (Article for reviews), inReplyToBook, readingStatus,
    tag[Edition], attachment[cover], name: 'Review of "…": Sterk'
```

It is byte-for-byte the same **pure representation** that a single-object fetch
returns (ADR 0007) — and it serves fifteen of them for one throttled request.
`enrich.parse_object()` reads outbox items with no changes at all.

So the expensive thing and the sparse thing and the shallow thing all had the
same fix, and it was not an optimisation of the timeline approach. It was a
different feed.

## Decision

**The feed is assembled from the ActivityPub outboxes of the BookWyrm accounts
the reader follows. The home timeline is no longer read.**

The governing principle of ADR 0002 survives in narrowed form:

> **You see a post because you follow that account.** Same as Mastodon, minus
> boosts.

Concretely:

- **The follow list is still read in the browser**, from the reader's own
  instance, with the reader's own token. `/api/v1/accounts/verify_credentials`
  and `/api/v1/accounts/:id/following`. It is used to decide whose outbox to ask
  for.
- **`POST /api/samling`** takes one actor URI and one page number and returns
  that page as cards. The URI must be on a nodeinfo-confirmed BookWyrm host — the
  same cache-only allowlist gate `/api/berik` uses, so the browser must have
  asked `/api/instansar` about the domain first (ADR 0003).
- **No crawler.** Retained from 0002, unchanged and non-negotiable. The server
  walks nothing on its own. Every outbox page is fetched because a reader is
  present and following that account. There is no background job.
- **No logged-out feed and no discovery surface.** Retained from 0002, unchanged.
  A stranger sees the explainer and the invented sample cards.
- **No post storage on the server.** Retained from 0002 and 0005, unchanged.
  Parsed posts go into the same in-memory TTL cache and leave with the process.
  Persistence is the reader's own browser and nowhere else — see ADR 0009.

### What the server now learns, stated plainly

**Actor URIs of accounts the reader follows.** This weakens the guarantee the
README used to make — *"the server never sees a token, a follow list, or a user
identity"* — and that sentence has been corrected rather than quietly left
standing. The token and the identity are still never seen. The follow list now
is, one actor at a time.

Two things bound it, and neither is an excuse:

- **It is not new in kind.** `/api/berik` already receives URIs of the form
  `https://bookwyrm.social/user/mvrkws/comment/123`. The server has always
  learned which actors a reader reads. What is new is that it learns the followed
  set *up front*, including accounts that have not posted lately.
- **The same handling applies.** No log line here or in uvicorn's access log, no
  storage, `Cache-Control: no-store`, and `cache_stats()` returns sizes only. The
  actor cache is keyed by actor URI and is memory-only for that reason.

### Two guards on the endpoint

Both are easy to undo while making the code look tidier, so they are named here
as well as in `app/outbox.py`:

- **The page number is an integer we build a URL from — never a URL from the
  caller.** The outbox hands us a `next` link, and passing it back to the browser
  to be returned on the next call is the obvious design. It would turn
  `/api/samling` into a way to fetch arbitrary paths on an allowlisted host.
- **The outbox must live on the actor's own host.** An actor document is remote
  input. One pointing its `outbox` at somebody else's server would make us a
  fetch amplifier aimed at a third party, from inside the allowlist.

## Consequences

Three things are lost, and they are visible in the UI copy rather than left to be
discovered:

- **Boosts are gone.** A book post boosted into your timeline by an ordinary
  Mastodon account you follow is in no followed BookWyrm actor's outbox. This is
  the clause of ADR 0002's principle that did not survive, and it is a real
  loss — boosts were how a book post from outside your follows reached you.
- **Followers-only posts are gone.** A public outbox contains public posts. The
  home timeline showed you followers-only posts you were entitled to see.
- **Cards have no Mastodon status id until asked for one.** An outbox item has
  only an ActivityPub URI, and favourite / boost / reply all need a local status
  id from the reader's instance. It is resolved **lazily**, on first interaction,
  via `/api/v2/search?resolve=true`. Never eagerly: that would be one instance
  request per card, and `resolve=true` makes the reader's instance fetch the
  remote object.

And the shape of the cost changed rather than vanishing:

- **Book lookups are now the slow part.** A cold page of fifteen posts mentioning
  eight new books took ~23 s in testing, almost all of it `books.ensure_book`;
  the same page with the books already in SQLite took ~3.5 s. Editions are shared
  between readers and cached permanently, so this amortises to nothing, but the
  first sweep of a new shelf is slow and the client must render progressively
  rather than waiting.
- **A deep shelf is deep.** 1092 items is 73 pages. The client goes breadth-first
  (page 1 of every followed actor) before depth, and round-robins the depth walk,
  so one prolific account cannot starve the rest.

**The tell that this decision is being undone** is the same as 0002's, minus the
clause this record spent: a database table with posts in it, or a background job
that fetches without a reader present. Either needs a new record superseding this
one. `tests/test_outbox.py::test_collecting_a_shelf_stores_no_posts` asserts the
first one directly.
