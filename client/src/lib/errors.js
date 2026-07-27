/**
 * The error taxonomy (5h), in one place.
 *
 * Two rules hold across all of it:
 *
 *   - No message mentions an HTTP code or the word "token". A reader cannot act
 *     on either. Hosts *are* named, because a host is the one thing they can.
 *   - A partial failure is never a blocking screen. The shelf shows what
 *     arrived.
 *
 * 401 is the one worth reading twice: an expired session does not log anybody
 * out and does not clear the collection. Reading continues from what is already
 * in the browser, and only the actions that need the network go quiet.
 */
import { warn } from './toast.svelte.js';

/** The status a failed call carried, or 0 when there was no answer at all. */
export function statusOf(error) {
  const status = Number(error?.status);
  return Number.isFinite(status) ? status : 0;
}

export function isUnauthorised(error) {
  return statusOf(error) === 401 || String(error?.message) === 'unauthorised';
}

export function isGone(error) {
  const status = statusOf(error);
  return status === 404 || status === 410;
}

/**
 * What to say when a write (favourite, boost, reply) did not go through.
 *
 * Returns the outcome so the caller can do the structural part — roll the
 * optimistic state back, drop a card that no longer exists — while the words
 * are decided here.
 */
export function reportWriteFailure(error) {
  if (isUnauthorised(error)) return 'expired';
  if (statusOf(error) === 403) {
    warn('error.forbidden');
    return 'rollback';
  }
  if (isGone(error)) {
    warn('error.gone');
    return 'gone';
  }
  warn('error.writeFailed');
  return 'rollback';
}

/**
 * How long to wait before trying a host again, from its `Retry-After`.
 *
 * The header is optional, and when it is missing we say five minutes and the
 * words "om lag" — a made-up precise number would be a lie with a colon in it.
 */
export function retryAfterSeconds(header) {
  if (!header) return { seconds: 300, exact: false };
  const asNumber = Number(header);
  if (Number.isFinite(asNumber) && asNumber >= 0) {
    return { seconds: Math.min(asNumber, 3600), exact: true };
  }
  const asDate = Date.parse(header);
  if (Number.isFinite(asDate)) {
    const seconds = Math.round((asDate - Date.now()) / 1000);
    if (seconds > 0) return { seconds: Math.min(seconds, 3600), exact: true };
  }
  return { seconds: 300, exact: false };
}

/** `03:47`, for the rate-limit countdown. */
export function clock(seconds) {
  const total = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(total / 60);
  return `${String(minutes).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}
