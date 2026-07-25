# Decision records

Short, append-only notes capturing decisions that are hard to re-derive from the
code alone — especially ones we learned the hard way. Each record explains *why*
a thing is the way it is, so we (and agents) don't undo it by accident later.

This is the **same practice used across every service on the Hetzner box** (the
central copy lives in `mmsge/hetzner-server`). Each repo keeps its **own** records,
about its **own** code. If a decision is about central ingress / routing / the box
itself, record it in `hetzner-server`; if it's about this service, record it here.

## Format

One file per decision: `NNNN-short-slug.md`, numbered in order. Each has:

- **Status** — `Accepted`, `Superseded by NNNN`, or `Deprecated`
- **Contributors** — who shaped the decision (see attribution rule below)
- **Context** — what happened / what forced the decision
- **Decision** — what we do, concretely
- **Consequences** — trade-offs and what to watch for

Records are immutable once accepted. To change a decision, add a new record and
mark the old one `Superseded by NNNN`.

## When to write one

- **An incident occurs** whose root cause is hard to re-derive from the code — a
  footgun someone could reintroduce. Record the symptom, the trap, and the fix.
- **A specific decision is made** — a deliberate choice between real alternatives
  (a convention, a config trade-off, why we do X instead of the obvious Y).

Skip routine changes with no trap and no alternative worth remembering.

## Contributors / attribution

The Contributors field must make it obvious **whether Markus requested the
decision or an agent made it without input**:

- List **Markus** only if he was *actively asked a question and gave an answer*
  that shaped the decision. Reporting a symptom or saying "fix it" does not count.
- Otherwise mark it an **agent decision** and name the agent, e.g.
  `Claude (agent decision — no human input on the technical choice)`.
- When both: `Markus (asked & decided: <choice>) + Claude (proposed/implemented)`.

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](0001-client-built-in-ci-not-on-the-box.md) | The Svelte client is built in CI and committed, never on the box | Accepted |
| [0002](0002-a-client-not-a-crawler.md) | Lesesalen is a client, not a service: no crawler, no logged-out feed | Superseded by [0008](0008-the-feed-is-the-followed-outboxes.md) |
| [0003](0003-berik-is-an-ssrf-boundary.md) | `/api/berik` is an SSRF boundary, and every guard on it is load-bearing | Accepted |
| [0004](0004-covers-are-re-encoded-on-ingest.md) | Cover images are raster-only and re-encoded on ingest | Accepted |
| [0005](0005-enrichment-cache-is-memory-only.md) | Post enrichment lives in memory only, and never on disk | Accepted |
| [0006](0006-no-trusted-types-in-the-csp.md) | `require-trusted-types-for 'script'` blanks the app in Chromium | Accepted |
| [0007](0007-the-uri-is-the-type-discriminator.md) | BookWyrm serves third parties a plain `Note`; the URI is the type | Accepted |
| [0008](0008-the-feed-is-the-followed-outboxes.md) | The feed is the outboxes of the accounts you follow, not your home timeline | Accepted |
| [0009](0009-the-collection-lives-in-the-readers-browser.md) | The collection persists in the reader's own browser, never on the server | Accepted |
| [0010](0010-cards-render-before-their-editions-are-fetched.md) | A card renders before its edition is fetched, from the cover attachment's name | Accepted |
| [0011](0011-outbox-pages-are-shared-between-readers.md) | Outbox pages are cached in memory and shared between readers | Accepted |
