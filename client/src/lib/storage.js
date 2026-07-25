/**
 * Where the token lives.
 *
 * localStorage by default; sessionStorage when the reader has ticked "log me
 * out when I close the tab", which matters on a shared machine. The preference
 * itself is always in localStorage, because it has to outlive the session it
 * describes.
 *
 * Be honest about the trade-off rather than pretending it away: a token in
 * localStorage is exposed to any successful XSS. That is accepted practice for
 * browser-based fediverse clients, and it is a better position than a server
 * holding thousands of tokens, but it is not free. The CSP and the sanitiser
 * are what make it survivable — see docs/decision-records/0004.
 */
const EPHEMERAL_KEY = 'lesesalen.ephemeral';

export function isEphemeral() {
  try {
    return window.localStorage.getItem(EPHEMERAL_KEY) === '1';
  } catch {
    return false;
  }
}

export function setEphemeral(value) {
  try {
    if (value) {
      window.localStorage.setItem(EPHEMERAL_KEY, '1');
      // Move anything already stored across, so ticking the box takes effect now.
      for (const key of SESSION_KEYS) {
        const existing = window.localStorage.getItem(key);
        if (existing !== null) {
          window.sessionStorage.setItem(key, existing);
          window.localStorage.removeItem(key);
        }
      }
    } else {
      window.localStorage.removeItem(EPHEMERAL_KEY);
      for (const key of SESSION_KEYS) {
        const existing = window.sessionStorage.getItem(key);
        if (existing !== null) {
          window.localStorage.setItem(key, existing);
          window.sessionStorage.removeItem(key);
        }
      }
    }
  } catch {
    /* storage unavailable: the app still works, it just will not remember */
  }
}

export const SESSION_KEYS = ['lesesalen.konto', 'lesesalen.app'];

function backing() {
  return isEphemeral() ? window.sessionStorage : window.localStorage;
}

export function read(key, fallback = null) {
  try {
    const raw = backing().getItem(key) ?? window.localStorage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function write(key, value) {
  try {
    backing().setItem(key, JSON.stringify(value));
  } catch {
    /* quota or private mode: not fatal */
  }
}

export function remove(key) {
  try {
    window.localStorage.removeItem(key);
    window.sessionStorage.removeItem(key);
  } catch {
    /* nothing to do */
  }
}
