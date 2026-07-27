/**
 * Lesesalen's own API. Four endpoints. No token is ever attached to any of them,
 * and there is nothing on the other end that could use one.
 *
 * Three take nothing that names a person: bare domain names, post URIs, book ids.
 * `collection()` is the exception — it takes the actor URI of somebody the reader
 * follows, because that is what an outbox walk is. ADR 0008 records that cost
 * rather than glossing it; the server logs none of it and stores none of it.
 */

/** 8 seconds, then one retry 2 seconds later, then it counts as a failure (5h). */
const TIMEOUT_MS = 8000;
const RETRY_AFTER_MS = 2000;

/**
 * A failed call, described well enough for the sweep notice to name the host
 * and say what to do — a timeout, a rate limit with its `Retry-After`, or an
 * instance that answered wrongly. The reader never sees the number.
 */
export class FetchProblem extends Error {
  constructor(kind, { status = 0, retryAfter = null, host = null } = {}) {
    super(kind);
    this.name = 'FetchProblem';
    /** 'tidsavbrot' | 'grense' | 'svikt' | 'ulesbar' */
    this.kind = kind;
    this.status = status;
    this.retryAfter = retryAfter;
    this.host = host;
  }
}

async function attempt(path, payload) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response;
  try {
    response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
  } catch (cause) {
    throw new FetchProblem(cause?.name === 'AbortError' ? 'tidsavbrot' : 'svikt');
  } finally {
    clearTimeout(timer);
  }

  if (response.status === 429) {
    throw new FetchProblem('grense', {
      status: 429,
      retryAfter: response.headers.get('retry-after'),
    });
  }
  if (!response.ok) throw new FetchProblem('svikt', { status: response.status });
  try {
    return await response.json();
  } catch {
    // A 200 that is not JSON is not something a retry fixes.
    throw new FetchProblem('ulesbar', { status: response.status });
  }
}

async function post(path, payload) {
  try {
    return await attempt(path, payload);
  } catch (problem) {
    // One quiet retry for a timeout, before anything appears on screen. Rate
    // limits and malformed answers are not made better by asking again at once.
    if (problem instanceof FetchProblem && problem.kind === 'tidsavbrot') {
      await new Promise((resolve) => setTimeout(resolve, RETRY_AFTER_MS));
      return attempt(path, payload);
    }
    throw problem;
  }
}

/**
 * Which of these domains run BookWyrm.
 *
 * Domains only — never the accounts they belong to, never how many posts came
 * from each. The server answers from a shared 30-day cache, so the same answer
 * serves everybody and the question is not attributable to a reader.
 */
export async function instances(domains) {
  const list = [...new Set(domains.filter(Boolean))];
  if (!list.length) return {};
  const data = await post('/api/instansar', { domener: list });
  return data.instansar || {};
}

/** Enrichment for a batch of BookWyrm status URIs, plus the books they mention. */
export async function enrich(uris) {
  const list = [...new Set(uris.filter(Boolean))];
  if (!list.length) return { entries: {}, books: {} };
  const data = await post('/api/berik', { uriar: list });
  return { entries: data.innslag || {}, books: data.boker || {} };
}

/**
 * One page of a followed actor's outbox, already parsed into cards.
 *
 * Fifteen posts for one request, where `enrich()` costs one origin fetch per
 * post. The page is a number, not a URL: the server builds every URL it fetches
 * from the actor's own outbox, and there is deliberately no parameter here that
 * would let the browser name a target (ADR 0008).
 */
export async function collection(actorUri, page = 1) {
  const data = await post('/api/samling', { aktor: actorUri, side: page });
  return {
    entries: data.innslag || [],
    books: data.boker || {},
    next: data.neste ?? null,
    total: data.totalt ?? null,
    pages: data.sider ?? null,
  };
}

/**
 * The editions we have, out of the ids asked for. Absent means "not yet".
 *
 * `/api/samling` answers before it has fetched the editions a page mentions, so
 * the client comes back for them. One request for a whole screen, and a missing
 * one is simply omitted rather than being a 404 per card.
 */
export async function books(ids) {
  const list = [...new Set(ids.filter(Boolean))];
  if (!list.length) return {};
  const data = await post('/api/boker', { ider: list });
  return data.boker || {};
}

export async function book(id) {
  const response = await fetch(`/api/bok/${encodeURIComponent(id)}`);
  if (!response.ok) return null;
  return response.json();
}
