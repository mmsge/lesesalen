# lesesalen

**A Mastodon web client that shows you only the book posts.**

BookWyrm has no public API, but it federates. Every BookWyrm post reaches a
Mastodon home timeline as a plain Note — with the rating, review title, quoted
passage, position and book link stripped out, because they are custom
ActivityPub properties Mastodon has no column for. Lesesalen re-fetches the
origin object and puts them back, as five distinct kinds of card.

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
- **No crawler, no logged-out feed, no post storage.** You see a post because
  you follow that account or someone you follow boosted it. Same as Mastodon
  (ADR 0002). The tell that this is being undone is a table with posts in it.
- **Post enrichment stays in memory.** Never write it to SQLite (ADR 0005).
- **The URI is the type discriminator, not the `type` field.** BookWyrm serves
  third parties a plain `Note`; trusting `type` collapses all five card kinds
  into one (ADR 0007).
- **The client is built in CI and committed to `client/dist`.** The box never
  runs Node. Edit `client/src`, run `make client`, commit the result (ADR 0001).

## Layout

```
app/            FastAPI server — the only reason it exists is that BookWyrm
                instances send no CORS headers for ActivityPub fetches
  netfetch.py   every outbound request, and every guard on them
  enrich.py     ActivityPub object -> the five card kinds
  books.py      bibliographic data + covers (raster-only, re-encoded)
  instances.py  nodeinfo probing; the allowlist everything else keys off
  sanitise.py   nh3, server side
  shell.py      index.html + per-route metadata + git-derived page dates
client/src/     Svelte 5 (runes). Built by CI, output committed to client/dist
tests/          pytest; the security guards are pinned here on purpose
```

## Common operations

```sh
make verify        # page dates + build + boot + healthz
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
- Expose an unauthenticated `GET /healthz` (returns `200 ok`) **and** keep the
  Compose `healthcheck:` that probes it. The probe dials `127.0.0.1`, never
  `localhost` (hetzner-server ADR 0010).
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
