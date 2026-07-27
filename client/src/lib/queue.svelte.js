/**
 * Replies written while offline, and the draft in the composer.
 *
 * A queued reply is shown with **its own text** — "«Denne passasjen har eg
 * tenkt på i tjue år» blir sendt når du er på nett att" — and with Rediger and
 * Forkast beside it. An anonymous "1 venter" tells the reader nothing about
 * what they will be publishing under their own name when the network returns.
 *
 * Both live in `localStorage` and both are cleared on log out.
 */
import { read, write, remove } from './storage.js';
import * as mastodon from './mastodon.js';
import { net } from './net.svelte.js';

const QUEUE_KEY = 'lesesalen.ko';
const DRAFT_KEY = 'lesesalen.utkast';

export const queue = $state({ items: read(QUEUE_KEY, []) || [] });

function persist() {
  write(QUEUE_KEY, queue.items);
}

export function enqueue(draft) {
  queue.items = [...queue.items.filter((held) => held.id !== draft.id), draft];
  persist();
}

export function dequeue(id) {
  queue.items = queue.items.filter((held) => held.id !== id);
  persist();
}

export function queuedFor(uri) {
  return queue.items.filter((held) => held.uri === uri);
}

/**
 * Send everything waiting, once there is a network again.
 *
 * A reply that fails for any reason other than "no network" is dropped from the
 * queue rather than retried forever: the reader would otherwise carry a ghost
 * reply between sessions with no way to see why it never went.
 */
export async function flush(account) {
  if (!account || !net.online || !queue.items.length) return;
  for (const draft of [...queue.items]) {
    if (!draft.inReplyToId) continue;
    try {
      await mastodon.reply(account, {
        inReplyToId: draft.inReplyToId,
        text: draft.text,
        visibility: draft.visibility,
        spoilerText: draft.warning,
      });
      dequeue(draft.id);
    } catch (error) {
      if (error?.status === 0) return; // still no network: leave the rest queued
      dequeue(draft.id);
    }
  }
}

// ── the composer's draft ────────────────────────────────────────────────────
//
// Saved whether the reader confirms the discard or not: "are you sure" is about
// leaving the screen, not about destroying what they wrote.

export function saveDraft(uri, draft) {
  const all = read(DRAFT_KEY, {}) || {};
  if (draft && draft.text?.trim()) all[uri] = draft;
  else delete all[uri];
  write(DRAFT_KEY, all);
}

export function loadDraft(uri) {
  const all = read(DRAFT_KEY, {}) || {};
  return all[uri] || null;
}

export function forgetQueue() {
  queue.items = [];
  remove(QUEUE_KEY);
  remove(DRAFT_KEY);
}
