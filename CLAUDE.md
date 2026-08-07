# lesesalen

**A Mastodon web client that shows you only the book posts.**

BookWyrm has no public API, but it federates. Its posts carry a rating, review
title, quoted passage, position and book link that Mastodon has no column for and
throws away. Lesesalen goes back to the origin ActivityPub objects and puts them
back, as five distinct kinds of card.

The feed is **the outboxes of the BookWyrm accounts you follow**, not your home
timeline: the follow list is read in the browser with the reader's own token, and
each actor's outbox is walked through `/api/samling`. One outbox page yields
fifteen already-rich objects, where the timeline needed one fetch per post
(ADR 0008).

## The rules that are not negotiable

These are the things most likely to be undone by a well-meaning change. Each has
an ADR; read it before working around it.

- **Never pass remote content to Svelte's `{@html}` unsanitised.**
  `client/src/components/RichText.svelte` is the *only* component allowed to use
  `{@html}`, and it runs DOMPurify with an allowlist first. The server sanitises
  the same content with `nh3` and the same allowlist. Two layers, deliberately:
  the token lives in `localStorage`, so one successful XSS is a full account
  compromise for whoever is using the app.
- **No `'unsafe-inline'` or `'unsafe-eval'` in `script-src`. Ever.** Not even
  briefly, while debugging. And do **not** add
  `require-trusted-types-for 'script'` back — it blanks the entire app in
  Chromium while looking fine in Firefox (ADR 0006).
- **`/api/berik` is an SSRF boundary.** Allowlist first, https only, address
  filtering with DNS pinning, redirect re-validation, size caps, and no request
  logging. Every guard is load-bearing (ADR 0003).
- **No crawler, no logged-out feed, no post storage.** You see a post because you
  follow that account (ADR 0008, superseding 0002 — which also said "or someone
  you follow boosted it", and boosts did not survive the move to outboxes). The
  server walks nothing on its own and there is no background job: every fetch
  happens because a reader is present. The tell that this is being undone is a
  table with posts in it.
- **Post enrichment stays in memory** on the server. Never write it to SQLite
  (ADR 0005). The reader's *browser* may persist their own collection in
  IndexedDB — and must not when `storage.isEphemeral()` is set (ADR 0009).
- **`/api/samling` builds its own URLs.** It takes an actor URI and an integer
  page, never a URL from the caller, and the actor's outbox must be on the
  actor's own host. Both stop it becoming a fetch primitive aimed through the
  allowlist (ADR 0008).
- **The URI is the type discriminator, not the `type` field.** BookWyrm serves
  third parties a plain `Note`; trusting `type` collapses all five card kinds
  into one (ADR 0007).
- **A card renders before its edition is fetched.** `outbox._parse_item` is
  synchronous and fetch-free, and `collect()` does not await `books.ensure_book`;
  author and title come off the cover attachment's name (`bok_kladd`), and the
  edition is resolved after the response. Re-adding that `await` looks like a
  tidy-up and silently restores a 23-second page load (ADR 0010).
- **`publisert` is the client's only date.** `parse_object` must keep returning
  the origin's `published`, or every card dates from 1970 *and* the feed sorts on
  `NaN` — which looks plausible and is not (ADR 0010).
- **A page number needs `positionMode: PG`.** `_position_mode` returns `None`
  when the object did not say, and `client/src/lib/progress.js` is the only
  place that decides whether a post has progress. Giving `_position_mode` a
  default puts invented page numbers on screen with nothing visibly broken
  (ADR 0012).
- **Nobody ever gave up on a book.** BookWyrm has no "stopped reading" event, so
  no surface states one. Inactivity is derived in the browser, labelled "Rekna ut
  av Lesesalen", and never carries a page number (ADR 0013).
- **A book looks the same everywhere.** Cloth, spine width and spine height are
  pure functions of the BookWyrm work id (`client/src/lib/spine.js`) — never of
  load order, an index, or `Math.random` (ADR 0014).
- **The client is built in CI and committed to `client/dist`.** The box never
  runs Node. Edit `client/src`, run `make client`, commit the result (ADR 0001).

## Layout

```
app/            FastAPI server — the only reason it exists is that BookWyrm
                instances send no CORS headers for ActivityPub fetches
  netfetch.py   every outbound request, and every guard on them
  enrich.py     ActivityPub object -> the five card kinds
  outbox.py     a followed actor's outbox -> a page of cards (the feed);
                pages are shared between readers for a few minutes (ADR 0011)
  books.py      bibliographic data + covers (raster-only, re-encoded)
  instances.py  nodeinfo probing; the allowlist everything else keys off
  sanitise.py   nh3, server side
  shell.py      index.html + per-route metadata + git-derived page dates
client/src/     Svelte 5 (runes). Built by CI, output committed to client/dist
  app.css       tokens, the shelf rail, and the one prefers-reduced-motion guard
  lib/progress.js  the only place that decides a post has a page position
  lib/stale.js     inactivity, derived and labelled as derived
  lib/spine.js     deterministic cloth and silhouette for a book without a cover
  lib/router.svelte.js  routes, filter history entries, scroll restoration
tests/          pytest; the security guards are pinned here on purpose
```

The client is **mobile-first** — every screen is drawn at 393px and grows into
the existing single 44rem column. Bottom tab bar under 44rem, back in the header
above it; sheets become panels; the review cover grows 132 → 168px.

## Common operations

```sh
make verify        # page dates + build info + build + boot + healthz/version/health
make test          # pytest
make client        # rebuild client/dist (commit the result)
make client-dev    # Vite dev server on :5173, proxying /api to :8080
make deploy        # on the server, in /srv/lesesalen
make remote-deploy # from a laptop, over SSH
```

## Deployment (Hetzner box)

| Key | Value |
|-----|-------|
| Slug / dir | `lesesalen` → `/srv/lesesalen` |
| Domain | `lesesalen.msge.no` |
| Host port | `4023` (bound `172.18.0.1:4023`) |
| Runtime | Docker Compose |
| Deploy | `cd /srv/lesesalen && make deploy` |

**Central ingress — do NOT manage TLS/routing here.** Caddy (TLS + reverse proxy
for every domain) is central in **`github.com/mmsge/hetzner-server`**. Do not add a
Caddy service to this repo. To change routing or the domain, edit that repo.

The security headers *are* set here rather than in Caddy, and that is
deliberate: they are application-specific (they describe this app's script and
connection model), and the box convention keeps service config out of central
ingress.

**Conventions this repo must follow:**
- Lives at `/srv/lesesalen`; the Compose project name is pinned (`name: lesesalen`)
  so a directory rename can never orphan named volumes.
- Publish the port on `172.18.0.1:4023` — never `127.0.0.1` (central Caddy dials
  it at `172.18.0.1:4023`).
- Set `mem_limit` (the box is 3.7 GB / 2 vCPU) and don't run heavy builds on it —
  which is exactly why the client is built in CI (ADR 0001).
- The base image is `python:3.12-slim`, not `-alpine`: `nh3` (Rust) and `Pillow`
  (C) have patchy musl wheel coverage, and a source build would drag a Rust
  toolchain onto the box.
- Expose the box's three unauthenticated ops endpoints — `GET /healthz`,
  `GET /version`, `GET /health` (hetzner-server ADR 0022) — and keep the Compose
  `healthcheck:` pointed at **`/healthz`**, never `/health`. The probe dials
  `127.0.0.1`, never `localhost` (hetzner-server ADR 0010).
  - `/healthz` returns exactly `ok` (two bytes, no newline — the healthcheck
    byte-compares it) and stays **dependency-free**: `return health()` would
    restart the container every time a BookWyrm instance is slow.
  - `/version` reports the *image's* git identity from the gitignored
    `build-info.json`, written by `scripts/generate-build-info.sh` on the
    checkout at `make deploy` **before** the build and `COPY`'d in **last** —
    `built_at` changes every deploy, so an earlier `COPY` would bust the
    `pip install` layer. Absent file ⇒ `source: "unknown"`, never a guess.
  - `/health` is **public**, so it is redacted by allowlist: ages, counts and a
    word from `main.DETAIL`, never a path, port, hostname, env name or
    `str(exc)`. `degraded` is a 200; only `error` is 503.
  - All three are registered above the `/{path:path}` SPA catch-all in
    `app/main.py`. Below it they would answer 200 with HTML, which the box's
    probe scores as *missing* rather than as broken.
- Serve `robots.txt` + `sitemap.xml` at the root, baked into the image — a
  selective `COPY` that omits them ships 404s.
- Every HTML page carries **git-derived creation/modification metadata** (the
  `meta name="date"`/`last-modified` pair, `article:published_time`/
  `article:modified_time`, JSON-LD `dateCreated`/`datePublished`/`dateModified`;
  `<lastmod>` in the sitemap). `scripts/generate-page-dates.sh` derives it on the
  checkout at `make deploy` (the image has no `.git`) into the gitignored
  `page-dates.json`; the app falls back to boot time when it's absent.
  `app/shell.py` injects it into the built `index.html` at request time. HTTP
  `Last-Modified` (+ 304) is served on the shell because the shell *is* static —
  all feed content is rendered client-side from the reader's own instance, so no
  live data ever sits behind that validator. See hetzner-server ADR 0015.

**Live data & full picture:** the box exposes a **Hetzner MCP at
`https://mcp.msge.no/mcp`** (bearer token). Call `get_service("lesesalen")`,
`list_services`, `next_free_port`, `port_map`, `conventions`, or `scaffold_service`
for authoritative, live answers. The static reference lives in `mmsge/hetzner-server`
(`Caddyfile` = the port map; `services/lesesalen-msge-no.md` = this service's doc).

## Decision records

Non-obvious knowledge — an incident whose root cause is hard to re-derive, or a
deliberate choice between real alternatives — lives in `docs/decision-records/` as
append-only ADRs (`NNNN-short-slug.md`; update the README index). This is the same
practice used across every service on the box. **Create one when:**

- **An incident** occurs whose cause is a footgun someone could reintroduce —
  record the symptom, the trap, and the fix.
- **A specific decision** is made — a convention or config trade-off, why X instead
  of the obvious Y.

Skip routine changes with no trap and no alternative worth remembering. Records are
immutable once accepted; to change one, add a new record and mark the old
`Superseded by NNNN`. The **Contributors** field must make clear whether Markus was
*asked and answered* (name him only then) or an **agent decided on its own** (name
the agent). Decisions about central ingress/routing/the box go in `hetzner-server`;
decisions about this service go here. See `docs/decision-records/README.md`.

## Language

UI copy is **Nynorsk first, English second**, in JSON catalogues at
`client/src/lib/locales/`. Nynorsk goes through the `nynorsk-profesjonell`
voice — sakleg and formal — not the conversational one.
