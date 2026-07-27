/**
 * Keep the keyboard inside a sheet while it is open, and let Escape out.
 *
 * A sheet that does not trap focus is a sheet a keyboard user tabs straight
 * out of, into a feed they cannot see because the sheet is over it. Focus goes
 * to the first control on open and back to whatever had it on close, so
 * dismissing a sheet puts you where you were.
 */
const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

export function trapFocus(node, onescape) {
  const previous = document.activeElement;

  function targets() {
    return [...node.querySelectorAll(FOCUSABLE)].filter(
      (element) => element.offsetParent !== null || element === document.activeElement,
    );
  }

  function onkeydown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      onescape?.();
      return;
    }
    if (event.key !== 'Tab') return;
    const list = targets();
    if (!list.length) return;
    const first = list[0];
    const last = list[list.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  // After the sheet's own entry animation has begun, so the focus ring is not
  // painted mid-slide.
  requestAnimationFrame(() => targets()[0]?.focus());
  node.addEventListener('keydown', onkeydown);

  return {
    destroy() {
      node.removeEventListener('keydown', onkeydown);
      if (previous instanceof HTMLElement && document.contains(previous)) previous.focus();
    },
  };
}
