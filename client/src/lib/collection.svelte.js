/**
 * The feed: the outboxes of the BookWyrm accounts the reader follows.
 *
 * All of it runs in the browser.
 *
 *  1. Read the follow list from the reader's own instance, with their own token.
 *  2. Collect the distinct domains and ask our server which run BookWyrm.
 *     Domains only — one probe answers for everybody and names nobody.
 *  3. For each account on a BookWyrm instance, walk its outbox through
 *     `/api/samling`. One request returns fifteen already-rich posts.
 *  4. Render, deduped and sorted by publication date.
 *
 * Why not the home timeline: it was mostly not books, it cost one throttled
 * origin fetch per post, and it only reached the slice the reader's instance had
 * delivered. What it gave that this does not is boosts and followers-only posts.
 * See ADR 0008.
 *
 * **Breadth before depth.** Page one of every followed shelf first, so a full
 * screen exists in seconds; only then walk deeper, round-robin across accounts so
 * one reader with a thousand posts cannot starve the other fourteen.
 *
 * The collection is remembered in the reader's own browser (`kista.js`, ADR 0009),
 * so the expensive first sweep is paid once.
 */
import * as kista from './kista.js';
import * as mastodon from './mastodon.js';
import * as server from './server.js';
import { retryAfterSeconds } from './errors.js';
import { net } from './net.svelte.js';

const FOLLOW_PAGES = 8; // up to ~640 follows; beyond that, ask for more explicitly
const DEEPEN_BATCH = 6; // outbox pages per "load more" round

export const feed = $state({
  items: [],
  books: {},
  loading: false,
  /** 'kvile' | 'fylgje' | 'instansar' | 'breidde' | 'djupn' */
  phase: 'kvile',
  shelves: 0, // BookWyrm accounts found
  sweeping: 0, // ...how many need their first page read this round
  swept: 0, // ...and how many of those are done
  exhausted: false,
  error: null,
  expired: false,
  restored: false, // rendered from the browser's own collection on load
  /**
   * Hosts that did not answer this round: `{ host, kind, until }`.
   *
   * A partial failure is never a blocking screen (§Errors) — the shelf shows
   * what arrived and this becomes a notice above it (4c), with the host named
   * because the host is the only thing the reader can act on.
   */
  failures: [],
  unreadable: 0, // posts that came back as something we could not parse
  followCount: 0, // how many accounts the reader follows, for the empty state
});

/** actor URI -> { account, page, done, total } */
const shelves = new Map();
const seen = new Set();
const bookwyrmDomains = new Map();
let followsRead = false;

function sortByDate() {
  feed.items.sort((a, b) => Date.parse(b.core.created_at) - Date.parse(a.core.created_at));
}

/**
 * The book, as far as we know it right now.
 *
 * A cover attachment's name already gave us author and title (`bok_kladd`), so a
 * card can be complete before its edition has been fetched — which is the whole
 * reason the feed no longer waits ~23 s for a page of unseen books. `omslag` and
 * `blurhash` are absent until the real record lands, so `Cover.svelte` shows its
 * placeholder and then fills in. Text first, cover follows.
 */
function bookOf(entry) {
  const real = entry.bok ? feed.books[entry.bok] : null;
  if (real) {
    // The edition record has no publication year, but the cover attachment's
    // name usually did. Nothing else fills this in, and an absent year is a
    // field the book sheet drops entirely rather than padding with a dash.
    if (!real.aar && entry.bok_kladd?.aar) return { ...real, aar: entry.bok_kladd.aar };
    return real;
  }
  if (!entry.bok_kladd) return null;
  return {
    id: entry.bok || null,
    tittel: entry.bok_kladd.tittel,
    forfattarar: entry.bok_kladd.forfattarar || [],
    format: entry.bok_kladd.format || null,
    aar: entry.bok_kladd.aar || null,
    omslag: null,
    blurhash: null,
    utkast: true, // the edition has not been fetched yet
  };
}

/**
 * An outbox entry, dressed as the Mastodon status the cards expect.
 *
 * The cards were written against a timeline and there is no reason to rewrite
 * them: everything they read off `core` exists here or is honestly absent.
 * `id`, `favourited` and `reblogged` are the exception — an outbox item has no
 * Mastodon status id, and it is filled in lazily on the first interaction with
 * the card (see `resolve()`).
 */
function itemOf(entry, account) {
  return {
    id: entry.kjelde,
    core: {
      uri: entry.kjelde,
      url: entry.kjelde,
      created_at: entry.publisert || null,
      account,
      sensitive: Boolean(entry.sensitiv),
      spoiler_text: entry.aatvaring || '',
      id: null,
      favourited: false,
      reblogged: false,
    },
    // Nothing in an outbox is a boost: it is the account's own output.
    boostedBy: null,
    enrichment: entry,
    book: bookOf(entry),
    resolved: false,
  };
}

function append(items) {
  let added = 0;
  for (const item of items) {
    if (!item.core.uri || seen.has(item.core.uri)) continue;
    seen.add(item.core.uri);
    feed.items.push(item);
    added += 1;
  }
  return added;
}

/**
 * Give a collected card the Mastodon status id its actions need.
 *
 * Lazy on purpose: `resolve=true` makes the reader's instance fetch the remote
 * object, so doing this for a whole screen would be a federated fetch per card,
 * paid for by their server.
 */
export async function resolve(account, item) {
  if (item.resolved || item.core.id) return item.core.id;
  item.resolved = true;
  const status = await mastodon.resolveStatus(account, item.core.uri);
  if (!status) return null;
  item.core.id = status.id;
  item.core.favourited = Boolean(status.favourited);
  item.core.reblogged = Boolean(status.reblogged);
  return status.id;
}

// ── the sweep ───────────────────────────────────────────────────────────────

/** Which of the accounts the reader follows are on BookWyrm instances. */
async function findShelves(account) {
  feed.phase = 'fylgje';
  const me = await mastodon.verifyCredentials(account);

  const follows = [];
  let cursor = null;
  for (let page = 0; page < FOLLOW_PAGES; page += 1) {
    const { accounts, maxId } = await mastodon.following(account, me.id, { maxId: cursor });
    follows.push(...accounts);
    if (!maxId || !accounts.length) break;
    cursor = maxId;
  }

  // The empty state says "we looked through the 214 accounts you follow", and
  // that number has to be the real one.
  feed.followCount = follows.length;

  feed.phase = 'instansar';
  const domains = [...new Set(follows.map(mastodon.accountDomain).filter(Boolean))];
  const unknown = domains.filter((domain) => !bookwyrmDomains.has(domain));
  if (unknown.length) {
    const answers = await server.instances(unknown);
    for (const domain of unknown) {
      bookwyrmDomains.set(domain, Boolean(answers[domain]?.bookwyrm));
    }
  }

  for (const who of follows) {
    if (!bookwyrmDomains.get(mastodon.accountDomain(who))) continue;
    const actor = mastodon.actorUri(who);
    if (!actor) continue;
    const known = shelves.get(actor);
    // A restored shelf keeps its page cursor; only the account snapshot refreshes.
    if (known) known.account = who;
    else shelves.set(actor, { account: who, page: 0, done: false, total: null, refresh: false });
  }
  feed.shelves = shelves.size;
  followsRead = true;
}

/**
 * One outbox page. Returns how many cards it produced.
 *
 * A shelf that refuses — gone, renamed, or on a host that turned out not to be
 * BookWyrm after all — is marked done rather than failing the sweep. One bad
 * account must not empty the feed.
 */
/**
 * Note that a host did not answer, once per host per round.
 *
 * The shelf is left un-done on a rate limit or a timeout: it can be retried,
 * and the notice offers exactly that. Only a shelf that answered wrongly is
 * given up on for this session.
 */
function noteFailure(actor, problem) {
  let host = actor;
  try {
    host = new URL(actor).hostname;
  } catch {
    /* an actor URI we could not parse is its own answer */
  }
  const kind = problem?.kind || 'svikt';
  const existing = feed.failures.find((entry) => entry.host === host);
  if (existing) return;
  const wait = kind === 'grense' ? retryAfterSeconds(problem.retryAfter) : null;
  feed.failures.push({
    host,
    kind,
    seconds: wait ? wait.seconds : null,
    exact: wait ? wait.exact : true,
    until: wait ? Date.now() + wait.seconds * 1000 : null,
  });
}

async function readPage(actor, shelf, { refresh = false } = {}) {
  // A refresh re-reads the first page for anything new without winding the
  // cursor back: the deep pages this reader has already walked stay walked.
  const page = refresh ? 1 : shelf.page + 1;
  let result;
  try {
    result = await server.collection(actor, page);
  } catch (problem) {
    noteFailure(actor, problem);
    if (problem?.kind === 'ulesbar') feed.unreadable += 1;
    // A host that is merely busy or slow keeps its place in the queue; one that
    // answered wrongly does not get asked again this session.
    if (problem?.kind === 'svikt') shelf.done = true;
    return 0;
  }

  shelf.page = Math.max(shelf.page, page);
  shelf.refresh = false;
  shelf.total = result.total ?? shelf.total;
  if (!result.next && !refresh) shelf.done = true;

  Object.assign(feed.books, result.books);
  const added = append(result.entries.map((entry) => itemOf(entry, shelf.account)));

  kista.putBooks(result.books);
  kista.putPosts(
    result.entries.map((entry) => ({
      uri: entry.kjelde,
      aktor: actor,
      publisert: entry.publisert || null,
      beriking: entry,
      konto: shelf.account,
    })),
  );
  kista.putActor({ aktor: actor, side: shelf.page, ferdig: shelf.done, totalt: shelf.total });
  return added;
}

/**
 * Shelves still worth reading from.
 *
 * A shelf restored from storage whose account is no longer in the follow list has
 * no account snapshot to render a byline from — the reader unfollowed them. Its
 * posts stay in the collection until they are evicted, but it is not walked
 * further: you see a post because you follow that account (ADR 0008).
 */
/**
 * Swap draft books for real editions once the server has fetched them.
 *
 * `/api/samling` returns immediately with whatever editions were already on
 * disk and resolves the rest behind the response, so the ones it did not have
 * appear a few seconds later. `/api/bok/<id>` 404s until then, which is why this
 * makes a few spaced attempts and then stops caring: a card with author and
 * title but no cover is a perfectly readable card, and the next visit will have
 * it from disk anyway.
 */
const BOOK_RETRIES = [1500, 4000, 10000];

function missingBooks() {
  const wanted = new Set();
  for (const item of feed.items) {
    const id = item.enrichment.bok;
    if (id && !feed.books[id]) wanted.add(id);
  }
  return [...wanted];
}

/**
 * Stop a draft book from gleaming forever.
 *
 * `Cover.svelte` shows the "looking up" sweep while `utkast` is set, because a
 * real cover may still be on its way. Once we have stopped asking, it is not on
 * its way, and the cover should settle into its synthesised jacket rather than
 * animating at an empty rectangle for the rest of the session.
 */
function settleDrafts() {
  for (const item of feed.items) {
    if (item.book?.utkast) item.book = { ...item.book, utkast: false };
  }
}

async function catchUpBooks(attempt = 0) {
  const wanted = missingBooks();
  if (!wanted.length || attempt >= BOOK_RETRIES.length) {
    settleDrafts();
    return;
  }
  await new Promise((resolve) => setTimeout(resolve, BOOK_RETRIES[attempt]));

  let found = {};
  try {
    found = await server.books(wanted);
  } catch {
    /* still resolving, or never will: the draft cards stand */
  }
  if (Object.keys(found).length) {
    Object.assign(feed.books, found);
    // `feed.items` is deeply reactive, so reassigning the book re-renders the
    // card with its cover.
    for (const item of feed.items) {
      const id = item.enrichment.bok;
      if (id && found[id]) item.book = found[id];
    }
    kista.putBooks(found);
  }
  if (missingBooks().length) await catchUpBooks(attempt + 1);
  else settleDrafts();
}

/**
 * Forget one card, because the instance says it no longer exists (404/410).
 *
 * Only that card, and only from this reader's own collection. Nothing else in
 * the app removes posts.
 */
export function drop(item) {
  const uri = item?.core?.uri;
  if (!uri) return;
  feed.items = feed.items.filter((held) => held.core.uri !== uri);
  seen.delete(uri);
  kista.dropPost(uri);
}

function unfinished() {
  return [...shelves.entries()].filter(([, shelf]) => !shelf.done && shelf.account);
}

/**
 * Read the collection back out of the browser before touching the network.
 *
 * The reader sees their feed immediately; the sweep then only has to fetch what
 * is new. In ephemeral mode there is nothing to read and this does nothing.
 */
export async function restore() {
  const { posts, actors, books } = await kista.loadAll();
  if (!posts.length) return;

  for (const book of books) feed.books[book.id] = book;
  for (const row of actors) {
    shelves.set(row.aktor, {
      account: null,
      page: row.side || 0,
      done: Boolean(row.ferdig),
      total: row.totalt ?? null,
      refresh: false,
    });
  }
  append(posts.map((row) => itemOf(row.beriking, row.konto)));
  sortByDate();
  feed.restored = true;
  feed.shelves = shelves.size;
}

/**
 * Assemble the feed. Safe to call repeatedly — it continues where it left off.
 *
 * The first call reads the follow list and sweeps page one of every shelf.
 * Later calls (infinite scroll) deepen, round-robin.
 */
export async function load(account) {
  if (feed.loading || feed.exhausted) return;
  // Offline is not an error: the collection in the browser is still a whole
  // library. We simply do not attempt requests that cannot succeed.
  if (!net.online) return;
  feed.loading = true;
  feed.error = null;
  feed.failures = [];
  feed.unreadable = 0;

  try {
    if (!followsRead) {
      await findShelves(account);
      if (!shelves.size) {
        feed.exhausted = true;
        return;
      }

      // Breadth first: one page from every shelf that has not been read yet.
      //
      // Run the hosts in parallel. The server paces each origin domain at one
      // request per second, and that is the politeness guarantee — but shelves on
      // *different* instances never contend for it, so waiting for one before
      // starting the next just wastes wall-clock. Within a host it stays strictly
      // sequential, which is what the throttle would enforce anyway.
      feed.phase = 'breidde';
      feed.swept = 0;
      const byHost = new Map();
      let queued = 0;
      for (const [actor, shelf] of shelves) {
        if (!shelf.account) continue;
        if (shelf.page !== 0 && !shelf.refresh) continue;
        const host = mastodon.accountDomain(shelf.account) || actor;
        if (!byHost.has(host)) byHost.set(host, []);
        byHost.get(host).push([actor, shelf]);
        queued += 1;
      }
      // On a restored visit most shelves already have a page, so count what this
      // round will actually fetch rather than the whole follow list.
      feed.sweeping = queued;
      await Promise.all(
        [...byHost.values()].map(async (queue) => {
          for (const [actor, shelf] of queue) {
            await readPage(actor, shelf, { refresh: shelf.refresh });
            feed.swept += 1;
            sortByDate();
          }
        }),
      );
      kista.prune();
      catchUpBooks();
      if (unfinished().length) return;
    }

    // Then depth, round-robin, so no single prolific shelf starves the rest.
    feed.phase = 'djupn';
    for (let round = 0; round < DEEPEN_BATCH; round += 1) {
      const pending = unfinished();
      if (!pending.length) {
        feed.exhausted = true;
        break;
      }
      const [actor, shelf] = pending[round % pending.length];
      await readPage(actor, shelf);
    }
    sortByDate();
    kista.prune();
    catchUpBooks();
  } catch (error) {
    // An expired session stops the sweep and nothing else. The collection stays
    // exactly where it is, the reader keeps reading it, and nobody is logged
    // out (§Errors, 5d).
    if (error?.status === 401 || String(error.message) === 'unauthorised') feed.expired = true;
    else feed.error = 'feed.error';
  } finally {
    feed.loading = false;
    feed.phase = 'kvile';
  }
}

/** How far through the shelves the deep walk has got, for the progress line. */
export function depth() {
  let read = 0;
  let total = 0;
  for (const shelf of shelves.values()) {
    read += shelf.page;
    total += shelf.total ? Math.ceil(shelf.total / 15) : shelf.page;
  }
  return { read, total };
}

/** How far back the collection reaches, for the tail block (4d). */
export function reach() {
  let oldest = null;
  for (const item of feed.items) {
    const at = Date.parse(item.core.created_at);
    if (!Number.isFinite(at)) continue;
    if (oldest === null || at < oldest) oldest = at;
  }
  return oldest === null ? null : new Date(oldest);
}

/**
 * Run the sweep again — pull-to-refresh, and the per-host retry in the notice.
 *
 * Every shelf gets its first page re-read for anything new. The deep pages
 * already walked are kept: refreshing must not cost the reader the back
 * catalogue they waited for.
 */
export function resweep() {
  followsRead = false;
  feed.exhausted = false;
  feed.failures = [];
  for (const shelf of shelves.values()) {
    shelf.refresh = true;
    shelf.done = false;
  }
}

export function reset() {
  feed.items = [];
  feed.books = {};
  feed.exhausted = false;
  feed.error = null;
  feed.expired = false;
  feed.restored = false;
  feed.shelves = 0;
  feed.sweeping = 0;
  feed.swept = 0;
  feed.failures = [];
  feed.unreadable = 0;
  feed.followCount = 0;
  feed.phase = 'kvile';
  shelves.clear();
  seen.clear();
  followsRead = false;
}

/** Forget the collection here and in the browser's storage. */
export async function forget() {
  reset();
  await kista.clear();
}

/**
 * The actor URI of `name@host`, without asking anybody.
 *
 * The person page is public: it has to render for a visitor with no session,
 * and without one there is no instance to look an account up at. BookWyrm's
 * actor URIs are `https://<host>/user/<name>` — the same shape enrich.py reads
 * post kinds out of — so that is what we try. When there *is* a session the
 * account's own `uri` is used instead, because that is authoritative.
 *
 * A guess that is wrong costs one 404 from our own server and an empty shelf.
 * It never becomes a fetch primitive: `/api/samling` still requires the host to
 * be a confirmed BookWyrm instance and still builds every URL itself (ADR 0008).
 */
export function guessActor(who) {
  const handle = typeof who === 'string' ? who : who?.acct || '';
  const [name, host] = String(handle).replace(/^@/, '').split('@');
  if (!name || !host || !/^[a-z0-9.-]+$/i.test(host)) return null;
  return `https://${host}/user/${encodeURIComponent(name)}`;
}

/**
 * One person's shelf, for the person page.
 *
 * Goes through the same outbox walk, so it reaches their whole back catalogue
 * rather than the recent slice the reader's instance happens to hold — and it
 * works with no session at all, because `/api/samling` needs no token.
 */
export async function shelfOf(who, pages = 2) {
  const actor = mastodon.actorUri(who) || guessActor(who);
  if (!actor) return { items: [], books: {} };

  const domain = mastodon.accountDomain(who) || new URL(actor).hostname.toLowerCase();
  if (domain && !bookwyrmDomains.has(domain)) {
    const answers = await server.instances([domain]);
    bookwyrmDomains.set(domain, Boolean(answers[domain]?.bookwyrm));
  }
  if (!bookwyrmDomains.get(domain)) return { items: [], books: {} };

  const items = [];
  const books = {};
  for (let page = 1; page <= pages; page += 1) {
    const result = await server.collection(actor, page);
    Object.assign(books, result.books);
    for (const entry of result.entries) {
      const item = itemOf(entry, who);
      item.book = entry.bok ? books[entry.bok] || null : null;
      items.push(item);
    }
    if (!result.next) break;
  }
  items.sort((a, b) => Date.parse(b.core.created_at) - Date.parse(a.core.created_at));
  return { items, books };
}
