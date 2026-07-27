/**
 * One toast at a time.
 *
 * A new toast replaces the previous one rather than stacking: a column of
 * stacked failures is unreadable, and the reader only ever needs the most
 * recent thing to have gone wrong. 2.5 s, then it goes on its own.
 */
export const toast = $state({ message: null, tone: 'ok', at: 0 });

let timer = null;

export function show(message, tone = 'ok') {
  if (!message) return;
  clearTimeout(timer);
  toast.message = message;
  toast.tone = tone;
  toast.at = Date.now();
  timer = setTimeout(dismiss, 2500);
}

export function warn(message) {
  show(message, 'warn');
}

export function dismiss() {
  clearTimeout(timer);
  toast.message = null;
}
