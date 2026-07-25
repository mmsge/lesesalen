/**
 * Lesesalen's own API. Three endpoints, none of which accept anything
 * identifying: bare domain names, post URIs, and book ids.
 *
 * No token is ever attached to these calls, and there is nothing on the other
 * end that could use one.
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

export async function book(id) {
  const response = await fetch(`/api/bok/${encodeURIComponent(id)}`);
  if (!response.ok) return null;
  return response.json();
}
