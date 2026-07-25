/**
 * OAuth against the reader's own instance. Entirely client-side.
 *
 * The token is minted by the reader's server, held by the reader's browser, and
 * sent only back to that same server. It never touches lesesalen.msge.no —
 * there is no login on the server side at all, and no user table for one to
 * write to.
 *
 * `client_secret` in a public client is not truly secret. We send it because
 * Mastodon requires it for the token exchange, and we send PKCE alongside so
 * that instances supporting it (4.3+) do not depend on the secret at all.
 */
import { read, write, remove } from './storage.js';

const APP_KEY = 'lesesalen.app';
const ACCOUNT_KEY = 'lesesalen.konto';
const PENDING_KEY = 'lesesalen.pending';

const SCOPES = 'read write:statuses write:favourites';
const CLIENT_NAME = 'Lesesalen';

export function redirectUri() {
  return `${window.location.origin}/attende`;
}

/** Accepts "chaos.social", "https://chaos.social/", "@me@chaos.social". */
export function normaliseDomain(input) {
  let value = String(input || '').trim().toLowerCase();
  if (!value) return null;
  value = value.replace(/^https?:\/\//, '');
  if (value.includes('@')) value = value.split('@').pop();
  value = value.split('/')[0].replace(/\.$/, '');
  if (!value || value.includes(' ') || !value.includes('.')) return null;
  if (!/^[a-z0-9.-]+$/.test(value)) return null;
  if (value.startsWith('-') || value.endsWith('-') || value.startsWith('.')) return null;
  return value;
}

function base64url(bytes) {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function randomString(byteLength) {
  return base64url(crypto.getRandomValues(new Uint8Array(byteLength)));
}

async function challengeFor(verifier) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  return base64url(new Uint8Array(digest));
}

async function registerApp(domain) {
  const cached = read(APP_KEY);
  if (cached && cached.domain === domain && cached.client_id) return cached;

  const body = new URLSearchParams({
    client_name: CLIENT_NAME,
    redirect_uris: redirectUri(),
    scopes: SCOPES,
    website: window.location.origin,
  });
  const response = await fetch(`https://${domain}/api/v1/apps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!response.ok) throw new Error('apps');
  const data = await response.json();
  if (!data.client_id) throw new Error('apps');
  const app = {
    domain,
    client_id: data.client_id,
    client_secret: data.client_secret || '',
  };
  write(APP_KEY, app);
  return app;
}

/** Step one: register, then hand the reader to their own instance. */
export async function begin(rawDomain) {
  const domain = normaliseDomain(rawDomain);
  if (!domain) throw new Error('domain');
  const app = await registerApp(domain);

  const verifier = randomString(64);
  const state = randomString(32);
  const challenge = await challengeFor(verifier);
  // sessionStorage, not localStorage: this is per-attempt, and it must not
  // outlive the tab that started it.
  window.sessionStorage.setItem(
    PENDING_KEY,
    JSON.stringify({ domain, state, verifier }),
  );

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: app.client_id,
    redirect_uri: redirectUri(),
    scope: SCOPES,
    state,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  });
  window.location.assign(`https://${domain}/oauth/authorize?${params}`);
}

/**
 * Step two: exchange the code at the instance.
 *
 * The `code` is cleared out of the URL before anything else happens — it must
 * not sit in the address bar, in history, or in a referrer.
 */
export async function complete(search) {
  const params = new URLSearchParams(search);
  const code = params.get('code');
  const state = params.get('state');
  const failure = params.get('error');
  window.history.replaceState({}, '', '/');
  if (failure) throw new Error('avvist');
  if (!code || !state) throw new Error('mangler');

  let pending;
  try {
    pending = JSON.parse(window.sessionStorage.getItem(PENDING_KEY) || 'null');
  } catch {
    pending = null;
  }
  window.sessionStorage.removeItem(PENDING_KEY);
  if (!pending || pending.state !== state) throw new Error('state');

  const app = read(APP_KEY);
  if (!app || app.domain !== pending.domain) throw new Error('app');

  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: app.client_id,
    redirect_uri: redirectUri(),
    code,
    code_verifier: pending.verifier,
    scope: SCOPES,
  });
  if (app.client_secret) body.set('client_secret', app.client_secret);

  const response = await fetch(`https://${pending.domain}/oauth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!response.ok) throw new Error('token');
  const data = await response.json();
  if (!data.access_token) throw new Error('token');

  const account = { domain: pending.domain, token: data.access_token };
  write(ACCOUNT_KEY, account);
  return account;
}

export function current() {
  const account = read(ACCOUNT_KEY);
  return account && account.token && account.domain ? account : null;
}

/** Revoke at the instance first, then clear storage — in that order. */
export async function logOut() {
  const account = current();
  const app = read(APP_KEY);
  if (account && app && app.client_id) {
    try {
      await fetch(`https://${account.domain}/oauth/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          client_id: app.client_id,
          client_secret: app.client_secret || '',
          token: account.token,
        }),
      });
    } catch {
      /* revocation is best-effort; clearing local state is not */
    }
  }
  remove(ACCOUNT_KEY);
  remove(APP_KEY);
  try {
    window.sessionStorage.removeItem(PENDING_KEY);
  } catch {
    /* nothing to do */
  }
}
