# 0009 — The collection persists in the reader's own browser, never on the server

- **Status:** Accepted
- **Date:** 2026-07-25
- **Contributors:** Markus (asked & decided: persist client-side in IndexedDB,
  with nothing new stored on the server) + Claude (proposed the options,
  implemented, and raised the shared-machine problem below)
- **Topics:** privacy, caching, storage, product

## Context

ADR 0008 made the feed a sweep over the outboxes of every BookWyrm account the
reader follows. A first sweep is expensive: fifteen accounts is fifteen throttled
outbox fetches before a full screen exists, and every new book edition on those
pages costs a further lookup. Doing that again on every page reload is both rude
to the origin instances and a poor reading experience.

The obvious fix is to persist the assembled feed. ADR 0005 says post enrichment
lives in memory and never on disk — so the question is whether that forbids this.

It does not, and the distinction is worth writing down because it is the kind
that gets collapsed by a well-meaning simplification. **ADR 0005 governs *our*
server.** Its concern is that lesesalen must not accumulate a corpus of other
people's reading: *"the difference between 'a cache that spares BookWyrm repeat
fetches' and 'a corpus of other people's book posts' is entirely a matter of how
long the rows live and whether they survive a restart."* That is a statement
about a third party holding data about people who never heard of it.

A browser cache is not that. It holds the reader's own feed, on the reader's own
machine, under the reader's own control — which is what every fediverse client
does, and what the reader's Mastodon web UI already does. Nobody's reading is
being aggregated by a third party; it is being remembered by the person who
already chose to follow them.

## Decision

**The assembled collection persists in IndexedDB in the reader's browser. The
server stores nothing new. ADR 0005 stands unchanged for the server side.**

Three object stores in `client/src/lib/kista.js`:

| Store | Key | Contents |
|---|---|---|
| `postar` | post URI | published date, parsed enrichment, book id, actor URI, author snapshot |
| `aktorar` | actor URI | last page walked, whether the shelf is exhausted, item total |
| `boker` | book id | the record `/api/bok/{id}` would return |

On load: render from `postar` immediately, then fetch page 1 of each followed
actor for what is new, and deepen only where `aktorar` says the shelf is not
finished. Rows are capped and the oldest evicted.

### It honours "log me out when I close the tab"

`storage.js` already has an ephemeral mode, and this is the part most likely to be
missed by a later change: **when `isEphemeral()` is set, IndexedDB is not touched
at all.** The collection stays in memory for the life of the tab.

That preference exists because the reader is on a shared machine. Writing a
durable, on-disk archive of *other people's* reading to a shared computer —
because the reader ticked a box asking for less persistence — would be a
straightforward betrayal of what they asked for. The token is not the only thing
worth clearing.

The collection is also cleared on logout, and from an explicit "tøm samlinga"
control in Settings.

## Consequences

- A reader in ephemeral mode pays for the sweep on every visit. That is the
  correct trade and it is what they asked for.
- The cache can go stale in one direction we cannot detect: a post deleted or
  edited at the origin stays as it was collected until it is evicted. A client
  reading a live timeline would have seen the deletion. This is a genuine
  regression from the timeline feed and the reason rows are capped and evicted
  rather than kept indefinitely.
- Private-browsing modes and quota exhaustion make IndexedDB fail. Every write is
  best-effort, the same way `storage.js` swallows quota errors: a reader with no
  usable storage gets the in-memory experience, not an error.
- **The tell that this has drifted into ADR 0005 territory** is any of these three
  stores appearing on the server — in SQLite, in a file, or in a cache that
  outlives the process.
