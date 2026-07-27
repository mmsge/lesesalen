/**
 * Instances this browser has talked to before, and a guess at what a typo meant.
 *
 * The list is local and never leaves the browser: it is a convenience for one
 * person on one device, not a directory. Each entry remembers what software the
 * nodeinfo probe found, and whether the probe succeeded at all — a brass dot on
 * the login screen means "we have spoken to this host", which is a stronger
 * claim than "you typed this once".
 *
 * Domain typos are the common way a login fails (5c), and they fail late and
 * confusingly: you get sent nowhere, or to a host that is not a fediverse
 * instance at all. So a near-miss is offered back as a suggestion.
 */
import { read, write, remove } from './storage.js';

const KEY = 'lesesalen.instansar';
const MAX = 5;

/** A handful of large public instances, purely as spelling targets. */
const WELL_KNOWN = [
  'mastodon.social',
  'mastodon.online',
  'chaos.social',
  'fosstodon.org',
  'hachyderm.io',
  'bookwyrm.social',
];

export const recent = $state({ list: read(KEY, []) || [] });

export function remember(domain, { software = null, version = null, reached = false } = {}) {
  const kept = recent.list.filter((entry) => entry.domain !== domain);
  recent.list = [{ domain, software, version, reached }, ...kept].slice(0, MAX);
  write(KEY, recent.list);
}

export function forgetInstances() {
  recent.list = [];
  remove(KEY);
}

/** Levenshtein, capped: we only care about one or two slipped keys. */
function distance(a, b) {
  if (Math.abs(a.length - b.length) > 2) return 99;
  let previous = Array.from({ length: b.length + 1 }, (_, index) => index);
  for (let i = 1; i <= a.length; i += 1) {
    const row = [i];
    for (let j = 1; j <= b.length; j += 1) {
      row[j] = Math.min(
        previous[j] + 1,
        row[j - 1] + 1,
        previous[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
    }
    previous = row;
  }
  return previous[b.length];
}

/** The domain they probably meant, or null when nothing is close enough. */
export function suggest(domain) {
  const typed = String(domain || '').toLowerCase();
  if (!typed) return null;
  const candidates = [...recent.list.map((entry) => entry.domain), ...WELL_KNOWN];
  let best = null;
  let bestDistance = 3;
  for (const candidate of new Set(candidates)) {
    if (candidate === typed) return null; // it was spelled right; the fault is elsewhere
    const found = distance(typed, candidate);
    if (found < bestDistance) {
      best = candidate;
      bestDistance = found;
    }
  }
  return best;
}
