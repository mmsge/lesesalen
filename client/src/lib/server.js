/**
 * Lesesalen's own API. Four endpoints. No token is ever attached to any of them,
 * and there is nothing on the other end that could use one.
 *
 * Three take nothing that names a person: bare domain names, post URIs, book ids.
 * `collection()` is the exception — it takes the actor URI of somebody the reader
 * follows, because that is what an outbox walk is. ADR 0008 records that cost
 * rather than glossing it; the server logs none of it and stores none of it.
 */

async function post(path, payload) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`http ${response.status}`);
  return response.json();
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

export async function book(id) {
  const response = await fetch(`/api/bok/${encodeURIComponent(id)}`);
  if (!response.ok) return null;
  return response.json();
}
