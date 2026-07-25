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

export async function homeTimeline(account, { maxId = null, limit = 40 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (maxId) params.set('max_id', maxId);
  const response = await call(account, `/api/v1/timelines/home?${params}`);
  const statuses = await response.json();
  return { statuses, maxId: nextMaxId(response, statuses) };
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
 * The reader's follow list, read in the browser for the "gather" action.
 * It is used to decide whose posts to ask the instance for, and is never sent
 * anywhere else.
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
