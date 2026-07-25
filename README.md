# Lesesalen

[![deployed](https://img.shields.io/endpoint?url=https://utrulla.msge.no/badge/mmsge/lesesalen)](https://lesesalen.msge.no)

**A Mastodon web client that shows you only the book posts.**

`lesesalen.msge.no` · slug `lesesalen` · port `4023`

Dark, warm, library after hours. Five kinds of book post, five distinct looks.
Quotations break the column entirely.

## What it is, and what it deliberately is not

BookWyrm has no public API, but it federates. Lesesalen reads your follow list in
your browser, keeps the accounts on BookWyrm instances, and assembles a feed from
**their own ActivityPub outboxes** — a reading room built for books instead of
for microblogging.

**It is a client, not a service.** The governing principle:

> You see a post because you follow that account. Same as Mastodon, minus boosts.

So there is no crawler, no logged-out feed and no discovery surface. The server
walks nothing on its own and there is no background job: every fetch happens
because a reader is present and follows that account. Those posts are public, but
public is not the same as consenting to be aggregated, indexed and re-served by a
third party the author never heard of. A stranger arriving at the site sees an
explainer and some invented sample cards, not other people's reading. See
[ADR 0008](docs/decision-records/0008-the-feed-is-the-followed-outboxes.md),
which supersedes 0002.

**Why outboxes and not the home timeline.** The timeline version cost one
throttled origin fetch per post, was mostly not books so the first screen was
thin, and only ever reached the slice your instance had delivered. An outbox page
returns **fifteen already-rich objects for one request**, and reaches the whole
back catalogue. What that gives up is boosts and followers-only posts — a boosted
book post is in nobody's followed outbox.

## The key technical insight

Mastodon discards BookWyrm's rich fields. A review arrives as a Status with
`content` HTML and nothing else — the rating, review title, quoted passage,
position and book link are custom ActivityPub properties Mastodon has no column
for.

But the origin object is public and addressable, and **its URI encodes its own
type**:

```
https://bookwyrm.social/user/mvrkws/generatednote/12091719   reading status
https://bookwyrm.social/user/mvrkws/comment/11996174         comment
https://bookwyrm.social/user/mvrkws/review/…                 review
https://bookwyrm.social/user/mvrkws/quotation/…              quotation
```

Fetching that URI with `Accept: application/activity+json` returns the object,
and `inReplyToBook` leads to the Edition with title, authors, cover, pages and
ISBN.

**And an outbox serves fifteen of them at once.** An actor document says where its
outbox is; the collection root says how big it is; each page hands back fifteen of
those same objects, newest first, in the same representation a single-object fetch
returns:

```
https://bookwyrm.social/user/mvrkws          → outbox: …/user/mvrkws/outbox
…/user/mvrkws/outbox                         → totalItems 1092, last: …?page=73
…/user/mvrkws/outbox?page=1                  → 15 orderedItems
```

That is the whole reason the feed is built the way it is. One throttled request
per fifteen posts instead of per one.

**The browser cannot do this, because BookWyrm instances do not send CORS
headers for ActivityPub fetches. That single fact is the entire reason a server
exists in this project.**

One wrinkle worth knowing before reading the parser: BookWyrm serves third
parties a *pure* representation where `type` is always `Note` and the rich
fields are folded into the rendered content. The URI segment is therefore the
real type discriminator, and the rating is reconstructed from the review's
`name`. See [ADR 0007](docs/decision-records/0007-the-uri-is-the-type-discriminator.md).

## Architecture

```
Browser (Svelte)                          Server (FastAPI)
  |                                          |
  |-- OAuth, follow list, replies, favs      |-- /api/instansar  (nodeinfo)
  |   straight to the user's own instance    |-- /api/samling    (outbox page)
  |   token never leaves the browser         |-- /api/berik      (AP re-fetch)
  |                                          |-- /api/bok/<id>   (book + cover)
  |--- actor URIs, post URIs, domains ------>|
  |<-- cards, book data ---------------------|
  |                                          |
IndexedDB: the reader's own collection    SQLite: instances, books
  (skipped in ephemeral mode)             Disk:   cover images
                                          Memory: parsed posts + actor
                                                  outbox URLs, both TTL'd
```

**The server never sees a token or a user identity.** There is no user table and
no login on the server side at all.

It does see **the actor URIs of accounts you follow**, one at a time, because
that is what `/api/samling` takes. That is a real cost of the outbox design and
[ADR 0008](docs/decision-records/0008-the-feed-is-the-followed-outboxes.md) states
it rather than glossing it: the mitigation is that `/api/berik` already received
URIs like `…/user/mvrkws/comment/123`, so which actors a reader reads was never
hidden — and that these URIs are logged nowhere, stored nowhere, and answered
`no-store`.

| Stored | Contents | Why it is acceptable |
|---|---|---|
| `instance` | domain, software, probed_at | Infrastructure metadata, not personal |
| `book` | title, authors, pages, isbn, cover, blurhash | A book edition is not anyone's personal information |
| cover files | Downloaded once at enrichment | No per-view tracking, no reader IP reaching the origin instance |

Post enrichment lives in an **in-memory LRU with a TTL** and is never written to
disk. A restart empties it, which is correct
([ADR 0005](docs/decision-records/0005-enrichment-cache-is-memory-only.md)). The
same holds for the actor cache `/api/samling` keeps — its keys are the actor URIs
of accounts somebody follows, so it is memory-only for exactly that reason.

The reader's assembled collection *does* persist, in **IndexedDB in their own
browser** — their own feed, on their own machine, like any fediverse client. Not
when they have ticked "log me out when I close the tab": that reader is on a
shared machine, and a durable on-disk archive of other people's reading is not
what they asked for
([ADR 0009](docs/decision-records/0009-the-collection-lives-in-the-readers-browser.md)).

## Security

Two things carry the weight of the whole design: the Content-Security-Policy,
and sanitisation of remote HTML. The token lives in `localStorage`, so one
successful XSS is a full account compromise for whoever is using the app.

- `script-src 'self'`, `object-src 'none'`, no `'unsafe-inline'`, no
  `'unsafe-eval'` — and **no `require-trusted-types-for 'script'`**, which
  blanks the entire app in Chromium
  ([ADR 0006](docs/decision-records/0006-no-trusted-types-in-the-csp.md)).
- Remote HTML is sanitised **twice**, allowlist-only: DOMPurify in the browser
  and `nh3` on the server. `RichText.svelte` is the only component permitted to
  use `{@html}`.
- `/api/berik` is treated as an SSRF boundary: allowlist first, https only,
  address filtering with DNS pinning, redirect re-validation, size caps, per-IP
  and per-domain rate limits, and no request logging — the URIs say what someone
  is reading ([ADR 0003](docs/decision-records/0003-berik-is-an-ssrf-boundary.md)).
- `/api/samling` sits behind the same boundary, plus two of its own. It takes an
  actor URI and an **integer** page and builds every URL it fetches itself —
  passing the outbox's `next` link back through the caller would make it a way to
  fetch arbitrary paths on an allowlisted host. And an actor's `outbox` must be on
  the actor's own host, or a hostile actor document turns us into a fetch
  amplifier aimed at a third party
  ([ADR 0008](docs/decision-records/0008-the-feed-is-the-followed-outboxes.md)).
- Covers are raster-only and re-encoded on ingest, because a malicious SVG
  served from our origin would be same-origin script
  ([ADR 0004](docs/decision-records/0004-covers-are-re-encoded-on-ingest.md)).

## Development

```sh
make test          # pytest
make client-dev    # Vite dev server on :5173, proxying /api to :8080
python -m uvicorn app.main:app --port 8080 --no-access-log   # the API

make client        # rebuild client/dist — commit the result (ADR 0001)
make verify        # page dates + docker build + boot + healthz
```

The Svelte client is **built in CI and committed** to `client/dist`; the box
never runs Node. CI rebuilds it and fails if the committed bundle is stale, so
edit `client/src`, run `make client`, and commit what it produces
([ADR 0001](docs/decision-records/0001-client-built-in-ci-not-on-the-box.md)).

Fonts are self-hosted and hand-subset to latin + latin-ext (`client/src/fonts.css`).
No CDN, anywhere: a CDN is a third party who can serve script into this origin,
which would defeat the CSP.

## Deployment

Lives at `/srv/lesesalen`, Docker Compose, bound to `172.18.0.1:4023`, behind
central Caddy. Routing and TLS are **not** managed here — they live in
[`mmsge/hetzner-server`](https://github.com/mmsge/hetzner-server). See
`CLAUDE.md` for the full box context.

```sh
cd /srv/lesesalen && make deploy
```

## Licence

AGPL-3.0 (`SPDX-License-Identifier: AGPL-3.0-or-later`) — see `LICENSE`. Keep the
`NOTICE` (it carries the AI-authorship disclosure). Built with AI —
[Laga med KI](https://msge.no/ki). Box-wide policy:
`hetzner-server/docs/licensing/` + ADR 0018.
