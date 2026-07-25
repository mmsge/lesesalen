/**
 * Feed assembly. All of it runs in the browser.
 *
 *  1. Read the home timeline from the reader's own instance.
 *  2. Collect the distinct domains of authors and of boosted authors, and ask
 *     our server which of them are BookWyrm. Domains only — never accounts.
 *  3. Keep statuses whose author is on a BookWyrm instance, or whose boosted
 *     author is. Boosts by ordinary Mastodon accounts are caught here naturally,
 *     because we are reading the live timeline while the reader is present.
 *  4. Ask our server to enrich the kept URIs.
 *  5. Render.
 *
 * On sparseness: a home timeline is mostly not books, so the first screen can
 * be thin. Two answers, both client-side. Deeper paging keeps pulling timeline
 * pages until enough book posts accumulate, with a visible state so it does not
 * look stalled. The gather action is explicit and reader-initiated, so the
 * default behaviour stays a pure timeline client.
 */
import * as mastodon from './mastodon.js';
import * as server from './server.js';

const TARGET_PER_LOAD = 8; // book posts we try to accumulate before stopping
const MAX_PAGES_PER_LOAD = 6; // ...and how far back we will page to get them

export const feed = $state({
  items: [],
  books: {},
  loading: false,
  digging: false, // paging deeper than the first page: shows "searching back"
  gathering: 0, // how many accounts a gather run is working through
  exhausted: false,
  error: null,
  expired: false,
});

let maxId = null;
const seen = new Set();
const bookwyrmDomains = new Map(); // domain -> boolean, for this session

/** The status that actually carries the content: the boosted one, if any. */
function inner(status) {
  return status.reblog || status;
}

async function classifyDomains(statuses) {
  const domains = new Set();
  for (const status of statuses) {
    const core = inner(status);
    const domain = mastodon.accountDomain(core.account);
    if (domain && !bookwyrmDomains.has(domain)) domains.add(domain);
  }
  if (!domains.size) return;
  const answers = await server.instances([...domains]);
  for (const domain of domains) {
    bookwyrmDomains.set(domain, Boolean(answers[domain]?.bookwyrm));
  }
}

function isBookPost(status) {
  const domain = mastodon.accountDomain(inner(status).account);
  return Boolean(domain && bookwyrmDomains.get(domain));
}

/** Merge enrichment into the statuses we kept, dropping the ones that were not. */
async function buildItems(candidates) {
  if (!candidates.length) return [];
  const uris = candidates.map((status) => inner(status).uri).filter(Boolean);
  const { entries, books } = await server.enrich(uris);
  Object.assign(feed.books, books);

  const items = [];
  for (const status of candidates) {
    const core = inner(status);
    const enrichment = entries[core.uri];
    if (!enrichment) continue; // not a book post after all, or unreachable
    items.push({
      id: status.id,
      status,
      core,
      boostedBy: status.reblog ? status.account : null,
      enrichment,
      book: enrichment.bok ? feed.books[enrichment.bok] || null : null,
    });
  }
  return items;
}

function append(items) {
  for (const item of items) {
    if (seen.has(item.core.uri)) continue;
    seen.add(item.core.uri);
    feed.items.push(item);
  }
}

/**
 * Pull timeline pages until we have enough book posts or run out of patience.
 * `digging` is true from the second page onward so the UI can say so.
 */
export async function loadMore(account) {
  if (feed.loading || feed.exhausted) return;
  feed.loading = true;
  feed.error = null;
  const before = feed.items.length;

  try {
    for (let page = 0; page < MAX_PAGES_PER_LOAD; page += 1) {
      feed.digging = page > 0;
      const { statuses, maxId: next } = await mastodon.homeTimeline(account, { maxId });
      if (!statuses.length) {
        feed.exhausted = true;
        break;
      }
      maxId = next;
      await classifyDomains(statuses);
      const candidates = statuses.filter(isBookPost).filter((s) => !seen.has(inner(s).uri));
      append(await buildItems(candidates));
      if (feed.items.length - before >= TARGET_PER_LOAD) break;
      if (!next) {
        feed.exhausted = true;
        break;
      }
    }
  } catch (error) {
    if (String(error.message) === 'unauthorised') feed.expired = true;
    else feed.error = 'feed.error';
  } finally {
    feed.loading = false;
    feed.digging = false;
  }
}

/**
 * The explicit gather: ask each BookWyrm account the reader follows for its own
 * posts, and merge them in.
 *
 * The follow list is read in the browser and used only to decide which accounts
 * to ask. It is never sent to our server — the server only ever learns bare
 * domain names, in batches.
 */
export async function gather(account) {
  if (feed.loading || feed.gathering) return;
  feed.error = null;
  try {
    const me = await mastodon.verifyCredentials(account);
    const follows = [];
    let cursor = null;
    for (let page = 0; page < 5; page += 1) {
      const { accounts, maxId: next } = await mastodon.following(account, me.id, { maxId: cursor });
      follows.push(...accounts);
      if (!next || !accounts.length) break;
      cursor = next;
    }

    const domains = [...new Set(follows.map(mastodon.accountDomain).filter(Boolean))];
    const unknown = domains.filter((domain) => !bookwyrmDomains.has(domain));
    if (unknown.length) {
      const answers = await server.instances(unknown);
      for (const domain of unknown) {
        bookwyrmDomains.set(domain, Boolean(answers[domain]?.bookwyrm));
      }
    }

    const bookish = follows.filter((who) => bookwyrmDomains.get(mastodon.accountDomain(who)));
    feed.gathering = bookish.length;
    if (!bookish.length) return;

    for (const who of bookish) {
      const { statuses } = await mastodon.accountStatuses(account, who.id, { limit: 20 });
      const candidates = statuses.filter((s) => !seen.has(inner(s).uri));
      append(await buildItems(candidates));
      feed.gathering -= 1;
    }
    sortByDate();
  } catch (error) {
    if (String(error.message) === 'unauthorised') feed.expired = true;
    else feed.error = 'feed.error';
  } finally {
    feed.gathering = 0;
  }
}

function sortByDate() {
  feed.items.sort(
    (a, b) => new Date(b.core.created_at).getTime() - new Date(a.core.created_at).getTime(),
  );
}

export function reset() {
  feed.items = [];
  feed.books = {};
  feed.exhausted = false;
  feed.error = null;
  feed.expired = false;
  maxId = null;
  seen.clear();
}

/** One person's book posts, fetched through the reader's own instance. */
export async function postsByAccount(account, accountId) {
  const { statuses } = await mastodon.accountStatuses(account, accountId, { limit: 40 });
  const uris = statuses.map((status) => inner(status).uri).filter(Boolean);
  const { entries, books } = await server.enrich(uris);
  const items = [];
  for (const status of statuses) {
    const core = inner(status);
    const enrichment = entries[core.uri];
    if (!enrichment) continue;
    items.push({
      id: status.id,
      status,
      core,
      boostedBy: status.reblog ? status.account : null,
      enrichment,
      book: enrichment.bok ? books[enrichment.bok] || null : null,
    });
  }
  return items;
}
