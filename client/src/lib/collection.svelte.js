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

const FOLLOW_PAGES = 8; // up to ~640 follows; beyond that, ask for more explicitly
const DEEPEN_BATCH = 6; // outbox pages per "load more" round

export const feed = $state({
  items: [],
  books: {},
  loading: false,
  /** 'kvile' | 'fylgje' | 'instansar' | 'breidde' | 'djupn' */
  phase: 'kvile',
  shelves: 0, // BookWyrm accounts found
  swept: 0, // ...and how many have had their first page read
  exhausted: false,
  error: null,
  expired: false,
  restored: false, // rendered from the browser's own collection on load
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
    book: entry.bok ? feed.books[entry.bok] || null : null,
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
    else shelves.set(actor, { account: who, page: 0, done: false, total: null });
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
async function readPage(actor, shelf) {
  const page = shelf.page + 1;
  let result;
  try {
    result = await server.collection(actor, page);
  } catch {
    shelf.done = true;
    return 0;
  }

  shelf.page = page;
  shelf.total = result.total ?? shelf.total;
  if (!result.next) shelf.done = true;

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
  feed.loading = true;
  feed.error = null;

  try {
    if (!followsRead) {
      await findShelves(account);
      if (!shelves.size) {
        feed.exhausted = true;
        return;
      }

      // Breadth first: one page from every shelf that has not been read yet.
      feed.phase = 'breidde';
      feed.swept = 0;
      for (const [actor, shelf] of shelves) {
        if (shelf.page === 0 && shelf.account) await readPage(actor, shelf);
        feed.swept += 1;
        sortByDate();
      }
      kista.prune();
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
  } catch (error) {
    if (String(error.message) === 'unauthorised') feed.expired = true;
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

export function reset() {
  feed.items = [];
  feed.books = {};
  feed.exhausted = false;
  feed.error = null;
  feed.expired = false;
  feed.restored = false;
  feed.shelves = 0;
  feed.swept = 0;
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
 * One person's shelf, for the author page.
 *
 * Goes through the same outbox walk, so it reaches their whole back catalogue
 * rather than the recent slice the reader's instance happens to hold.
 */
export async function shelfOf(who, pages = 2) {
  const actor = mastodon.actorUri(who);
  if (!actor) return { items: [], books: {} };

  const domain = mastodon.accountDomain(who);
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
