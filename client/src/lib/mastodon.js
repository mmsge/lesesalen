/**
 * The reader's own instance. Every call here carries the reader's token and
 * goes straight from their browser to their own server.
 *
 * Nothing in this file talks to lesesalen.msge.no. That separation is the whole
 * privacy model: the follow graph, the timeline and the token are the reader's
 * business, and the server we run never sees any of them.
 */

function authHeaders(account) {
  return { Authorization: `Bearer ${account.token}` };
}

async function call(account, path, options = {}) {
  const response = await fetch(`https://${account.domain}${path}`, {
    ...options,
    headers: { ...authHeaders(account), ...(options.headers || {}) },
  });
  if (response.status === 401) throw new Error('unauthorised');
  if (!response.ok) throw new Error(`http ${response.status}`);
  return response;
}

/** Mastodon pages by `max_id`; we follow its Link header rather than guessing. */
function nextMaxId(response, statuses) {
  const link = response.headers.get('link') || '';
  const match = link.match(/max_id=(\d+)[^>]*>;\s*rel="next"/);
  if (match) return match[1];
  return statuses.length ? statuses[statuses.length - 1].id : null;
}

export async function accountStatuses(account, accountId, { maxId = null, limit = 40 } = {}) {
  const params = new URLSearchParams({ limit: String(limit), exclude_replies: 'false' });
  if (maxId) params.set('max_id', maxId);
  const response = await call(account, `/api/v1/accounts/${accountId}/statuses?${params}`);
  const statuses = await response.json();
  return { statuses, maxId: nextMaxId(response, statuses) };
}

export async function verifyCredentials(account) {
  const response = await call(account, '/api/v1/accounts/verify_credentials');
  return response.json();
}

/**
 * The reader's follow list, read in the browser. This is what the feed is built
 * from: keep the accounts on BookWyrm instances, then walk their outboxes
 * (ADR 0008).
 *
 * Only the actor URIs of the BookWyrm accounts leave the browser, one at a time,
 * to `/api/samling`. The rest of the follow list — who else the reader follows,
 * and how many — never goes anywhere.
 */
export async function following(account, accountId, { maxId = null, limit = 80 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (maxId) params.set('max_id', maxId);
  const response = await call(account, `/api/v1/accounts/${accountId}/following?${params}`);
  const accounts = await response.json();
  const link = response.headers.get('link') || '';
  const match = link.match(/max_id=(\d+)[^>]*>;\s*rel="next"/);
  return { accounts, maxId: match ? match[1] : null };
}

export async function lookupAccount(account, acct) {
  const response = await call(account, `/api/v1/accounts/lookup?acct=${encodeURIComponent(acct)}`);
  return response.json();
}

/**
 * The reader's instance's own copy of a post, found by its ActivityPub URI.
 *
 * A post collected from an outbox has no Mastodon status id, and favouriting,
 * boosting and replying all need one. This is the only way to get it.
 *
 * Called lazily — on the first interaction with a card, never for a whole
 * screenful. `resolve=true` makes the reader's instance go and fetch the remote
 * object if it does not have it, so doing this eagerly would be one federated
 * fetch per card, paid for by their server.
 */
export async function resolveStatus(account, uri) {
  const params = new URLSearchParams({
    q: uri,
    type: 'statuses',
    resolve: 'true',
    limit: '1',
  });
  const response = await call(account, `/api/v2/search?${params}`);
  const found = await response.json();
  return (found.statuses || [])[0] || null;
}

export async function favourite(account, statusId, on) {
  const verb = on ? 'favourite' : 'unfavourite';
  const response = await call(account, `/api/v1/statuses/${statusId}/${verb}`, { method: 'POST' });
  return response.json();
}

export async function boost(account, statusId, on) {
  const verb = on ? 'reblog' : 'unreblog';
  const response = await call(account, `/api/v1/statuses/${statusId}/${verb}`, { method: 'POST' });
  return response.json();
}

/**
 * Replies only. Mastodon cannot mint BookWyrm objects — a reply from here is a
 * Mastodon post that mentions the book post, not a BookWyrm comment. The UI
 * says so plainly next to the composer rather than letting anyone find out
 * afterwards.
 */
export async function reply(account, { inReplyToId, text, visibility = 'public', spoilerText = '' }) {
  const body = new URLSearchParams({
    status: text,
    in_reply_to_id: inReplyToId,
    visibility,
  });
  if (spoilerText) body.set('spoiler_text', spoilerText);
  const response = await call(account, '/api/v1/statuses', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      // A retry must not post twice.
      'Idempotency-Key': `${inReplyToId}:${text}`.slice(0, 200),
    },
    body,
  });
  return response.json();
}

/**
 * An account's ActivityPub id — the thing whose outbox we can ask for.
 *
 * `uri` is the actor id and is what we want; Mastodon has only served it since
 * 4.2, so fall back to `url`. On BookWyrm the two are the same string
 * (`https://bookwyrm.social/user/x`), which is why the fallback is safe here.
 */
export function actorUri(account) {
  const candidate = account?.uri || account?.url;
  return typeof candidate === 'string' && candidate.startsWith('https://') ? candidate : null;
}

/** The host that actually served an account, which is what identifies its software. */
export function accountDomain(account) {
  if (!account) return null;
  try {
    return new URL(account.url).hostname.toLowerCase();
  } catch {
    const parts = String(account.acct || '').split('@');
    return parts.length > 1 ? parts[1].toLowerCase() : null;
  }
}
