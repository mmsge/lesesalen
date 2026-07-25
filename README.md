# Lesesalen

[![deployed](https://img.shields.io/endpoint?url=https://utrulla.msge.no/badge/mmsge/lesesalen)](https://lesesalen.msge.no)

**A Mastodon web client that shows you only the book posts.**

`lesesalen.msge.no` · slug `lesesalen` · port `4023`

Dark, warm, library after hours. Five kinds of book post, five distinct looks.
Quotations break the column entirely.

## What it is, and what it deliberately is not

BookWyrm has no public API, but it federates. Every BookWyrm post reaches your
Mastodon home timeline as a plain Note. Lesesalen is a Mastodon client that
shows you those posts and nothing else, in a reading room built for books
instead of for microblogging.

**It is a client, not a service.** The governing principle:

> You see a post because you follow that account, or because someone you follow
> boosted it. Same as Mastodon. Nothing more.

So there is no crawler, no logged-out feed and no discovery surface. Those posts
are public, but public is not the same as consenting to be aggregated, indexed
and re-served by a third party the author never heard of. A stranger arriving at
the site sees an explainer and some invented sample cards, not other people's
reading. The one broadening is clicking an author to see their posts — a normal
client affordance that goes through the reader's own instance with the reader's
own token. See [ADR 0002](docs/decision-records/0002-a-client-not-a-crawler.md).

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
  |-- OAuth, timeline, replies, favs         |-- /api/instansar  (nodeinfo)
  |   straight to the user's own instance    |-- /api/berik      (AP re-fetch)
  |   token never leaves the browser         |-- /api/bok/<id>   (book + cover)
  |                                          |
  |------- post URIs, domains -------------->|
  |<------ enrichment, book data ------------|
                                             |
                                    SQLite: instances, books
                                    Disk:   cover images
                                    Memory: parsed posts, TTL
```

**The server never sees a token, a follow list, or a user identity.** There is no
user table. There is no login on the server side at all.

| Stored | Contents | Why it is acceptable |
|---|---|---|
| `instance` | domain, software, probed_at | Infrastructure metadata, not personal |
| `book` | title, authors, pages, isbn, cover, blurhash | A book edition is not anyone's personal information |
| cover files | Downloaded once at enrichment | No per-view tracking, no reader IP reaching the origin instance |

Post enrichment lives in an **in-memory LRU with a TTL** and is never written to
disk. A restart empties it, which is correct
([ADR 0005](docs/decision-records/0005-enrichment-cache-is-memory-only.md)).

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
