/**
 * Pull down at the top of the feed to run the sweep again.
 *
 * Only from the very top, and only downwards: anywhere else this would fight
 * with the scroll the reader actually wants. Past 55px the indicator changes
 * its wording, and releasing there re-runs the sweep.
 *
 * An action rather than markup handlers, because the element it hangs on is a
 * plain container: giving a `<div>` touch handlers means giving it a role it
 * does not have, and a gesture is behaviour rather than semantics.
 */
const THRESHOLD = 55;
const RESISTANCE = 0.5;
const MAX = 90;

export function pullToRefresh(node, options) {
  let onmove = options?.onmove;
  let onrelease = options?.onrelease;
  let enabled = options?.enabled ?? true;
  let from = null;
  let distance = 0;

  function start(event) {
    from = enabled && window.scrollY <= 0 ? event.touches[0].clientY : null;
    distance = 0;
  }

  function move(event) {
    if (from === null) return;
    const travelled = event.touches[0].clientY - from;
    distance = travelled > 0 ? Math.min(travelled * RESISTANCE, MAX) : 0;
    onmove?.(distance);
  }

  function end() {
    if (from !== null && distance > THRESHOLD) onrelease?.();
    from = null;
    distance = 0;
    onmove?.(0);
  }

  node.addEventListener('touchstart', start, { passive: true });
  node.addEventListener('touchmove', move, { passive: true });
  node.addEventListener('touchend', end);
  node.addEventListener('touchcancel', end);

  return {
    update(next) {
      onmove = next?.onmove;
      onrelease = next?.onrelease;
      enabled = next?.enabled ?? true;
    },
    destroy() {
      node.removeEventListener('touchstart', start);
      node.removeEventListener('touchmove', move);
      node.removeEventListener('touchend', end);
      node.removeEventListener('touchcancel', end);
    },
  };
}

export const PULL_THRESHOLD = THRESHOLD;
