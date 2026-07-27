/**
 * Make a whole card open its post, from a tap or from the keyboard.
 *
 * The design is tap-anywhere: the card is the target, and the buttons inside it
 * stop the event. That means the card itself has to be reachable without a
 * mouse, so it takes `role="link"`, a tab stop and Enter/Space — the same
 * contract a link has, on an element that cannot be a link because it contains
 * buttons and a link may not.
 *
 * A drag or a long press is not a tap: if the pointer moved more than a few
 * pixels, or the press was long enough to be the book sheet's, the click is let
 * go. Otherwise every attempt to select a quotation would navigate away.
 */
const MOVED = 8;
const LONG_PRESS = 420;

export function openable(node, options) {
  let onopen = options?.onopen;
  let label = options?.label;
  let from = null;
  let at = 0;

  /**
   * Without a destination the card is not a control and must not pretend to be
   * one: a derived "hasn't touched this since March" line has no post behind it,
   * so it gets no role, no tab stop and no pointer.
   */
  function describe() {
    if (onopen) {
      node.setAttribute('role', 'link');
      node.setAttribute('tabindex', '0');
      if (label) node.setAttribute('aria-label', label);
    } else {
      node.removeAttribute('role');
      node.removeAttribute('tabindex');
      node.removeAttribute('aria-label');
    }
  }

  describe();

  function onpointerdown(event) {
    from = { x: event.clientX, y: event.clientY };
    at = Date.now();
  }

  function onclick(event) {
    // A button inside the card has already stopped its own event; anything that
    // reaches here is the card.
    if (event.defaultPrevented) return;
    if (from) {
      const moved =
        Math.abs(event.clientX - from.x) > MOVED || Math.abs(event.clientY - from.y) > MOVED;
      if (moved || Date.now() - at >= LONG_PRESS) {
        from = null;
        return;
      }
    }
    if (window.getSelection?.()?.toString()) return;
    from = null;
    onopen?.();
  }

  function onkeydown(event) {
    if (event.target !== node) return;
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    onopen?.();
  }

  node.addEventListener('pointerdown', onpointerdown);
  node.addEventListener('click', onclick);
  node.addEventListener('keydown', onkeydown);

  return {
    update(next) {
      onopen = next?.onopen;
      label = next?.label;
      describe();
    },
    destroy() {
      node.removeEventListener('pointerdown', onpointerdown);
      node.removeEventListener('click', onclick);
      node.removeEventListener('keydown', onkeydown);
    },
  };
}
