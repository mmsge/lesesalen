# 0002 — Lesesalen is a client, not a service: no crawler, no logged-out feed

- **Status:** Superseded by [0008](0008-the-feed-is-the-followed-outboxes.md)
- **Date:** 2026-07-25
- **Contributors:** Claude (agent decision — no human input on the technical
  choice; the governing principle and its consequences were stated in the
  project brief and are recorded here so they survive the first feature request
  that would quietly undo them)
- **Topics:** privacy, architecture, activitypub, bookwyrm, product

## Context

Lesesalen shows BookWyrm posts. BookWyrm posts are public ActivityPub objects,
and there is nothing technically stopping a server from walking the fediverse,
collecting every BookWyrm review it can reach into a database, and serving a
lovely browsable index of them.

That would also make the product obviously better on first contact: a logged-out
visitor would see a rich feed instead of an explainer, sparse timelines would
stop being a problem, and search would become possible. Every one of those is a
reasonable-sounding feature request, and each one individually looks small.

## Decision

**The governing principle: you see a post because you follow that account, or
because someone you follow boosted it. Same as Mastodon. Nothing more.**

Concretely, and non-negotiably:

- **No crawler.** The server never walks the fediverse and never collects posts
  it was not asked about while a reader was present. Public is not the same as
  consenting to be aggregated, indexed and re-served by a third party the author
  never heard of. A BookWyrm user posting a review to their followers did not
  sign up to be in somebody's corpus.
- **No logged-out feed and no discovery surface.** A stranger arriving at the
  site sees an explainer and invented sample cards (`client/src/lib/samples.js`),
  never other people's reading.
- **No post storage.** Enrichment lives in an in-memory TTL cache and is never
  written to disk (ADR 0005). What *is* persisted is instance nodeinfo
  (infrastructure) and bibliographic data plus covers (a book edition is not
  anyone's personal information).
- **The one broadening: click an author, see their posts.** This is a normal
  client affordance. It goes through the reader's own instance with the reader's
  own token and shows exactly what Mastodon would show. The server's only
  involvement is the same enrichment every other card gets.

## Consequences

- The first screen can be thin, because a home timeline is mostly not books.
  Two answers, both client-side: deeper paging with a visible "leitar bakover"
  state, and an explicit reader-initiated gather. Neither requires server-side
  storage, and the default behaviour stays a pure timeline client.
- There is no search, no "popular reviews", no trending books, and no way to
  read Lesesalen without an account. These are not gaps to be filled in later.
- **The tell that this decision is being undone:** a database table with posts
  in it, a background job that fetches without a reader present, or any endpoint
  that returns content the caller did not already have a URI for. If a change
  needs one of those, it needs a new ADR superseding this one — not a quiet
  extension.
