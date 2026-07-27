/**
 * A router small enough to read in one sitting.
 *
 * Two things it does that a smaller one would not:
 *
 * **Filters live in the query string**, so a view is linkable and survives a
 * reload: `/?type=sitat&person=@x@host` is a shareable bookmark of "quotations
 * from this person". Each filter change is its own history entry, so back
 * removes the last filter rather than leaving the app.
 *
 * **Scroll position is remembered per history entry.** Coming back from a post
 * detail must land you where you were reading, not at the top of a feed you
 * then have to find your place in again. The position is keyed on the history
 * entry rather than on the path, so two visits to the same feed do not fight
 * over one number.
 *
 * Back never traps: every sheet and every filter is an entry you can reverse,
 * and a feed with no filters is the last entry before the app.
 */
export const route = $state({
  path: window.location.pathname,
  query: Object.fromEntries(new URLSearchParams(window.location.search)),
});

/** history entry key -> scrollY */
const positions = new Map();
let counter = 0;

function keyOf() {
  const state = window.history.state;
  if (state && typeof state.lesesalen === 'number') return state.lesesalen;
  // A first load, or an entry somebody else pushed: adopt it.
  counter += 1;
  window.history.replaceState({ ...(state || {}), lesesalen: counter }, '');
  return counter;
}

let current = keyOf();

function remember() {
  positions.set(current, window.scrollY);
}

function sync() {
  route.path = window.location.pathname;
  route.query = Object.fromEntries(new URLSearchParams(window.location.search));
}

/**
 * Put the reader back where they were reading.
 *
 * Not in one frame: the view for the entry we have just returned to has to
 * render before the page is tall enough to scroll to, and `scrollTo` past the
 * bottom of a short document silently clamps to 0 — which lands you at the top
 * of a feed you then have to find your place in again. So we keep asking until
 * it takes, and give up after a few frames rather than fighting a page that
 * genuinely is shorter now.
 */
const RESTORE_MS = 2000;
let restoring = null;

function restoreScroll(wanted) {
  clearInterval(restoring);
  if (wanted <= 0) return;
  const until = Date.now() + RESTORE_MS;

  const attempt = () => {
    window.scrollTo({ top: wanted, behavior: 'instant' });
    // Landed, ran out of patience, or the reader started scrolling themselves —
    // in which case they have taken over and we get out of the way.
    if (Math.abs(window.scrollY - wanted) < 2 || Date.now() > until) {
      clearInterval(restoring);
      restoring = null;
    }
  };

  attempt();
  if (Math.abs(window.scrollY - wanted) < 2) return;
  restoring = setInterval(attempt, 50);
}

// The reader scrolling for themselves ends any restore in progress.
window.addEventListener(
  'wheel',
  () => {
    clearInterval(restoring);
    restoring = null;
  },
  { passive: true },
);

window.addEventListener('popstate', () => {
  remember();
  current = keyOf();
  sync();
  const wanted = positions.get(current) ?? 0;
  if (wanted > 0) requestAnimationFrame(() => restoreScroll(wanted));
  else window.scrollTo({ top: 0, behavior: 'instant' });
});

// Browsers restore scroll themselves on reload, which fights with the above.
if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual';

function urlFor(path, query) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && value !== '') params.set(key, value);
  }
  const search = params.toString();
  return search ? `${path}?${search}` : path;
}

/**
 * Go somewhere.
 *
 * `replace` is for the OAuth callback and nothing else: the authorisation code
 * must not stay in history where a back button can replay it.
 */
export function navigate(path, query = {}, { replace = false, keepScroll = false } = {}) {
  remember();
  const url = urlFor(path, query);
  if (replace) {
    window.history.replaceState({ lesesalen: current }, '', url);
  } else {
    counter += 1;
    current = counter;
    window.history.pushState({ lesesalen: current }, '', url);
  }
  sync();
  if (!keepScroll) window.scrollTo({ top: 0 });
}

/**
 * Change the query string in place, keeping the path.
 *
 * Filter changes push by default — that is what makes each of them separately
 * undoable with back (§Interactions).
 */
export function setQuery(query, { replace = false } = {}) {
  navigate(route.path, query, { replace, keepScroll: true });
}

/**
 * The current history entry's key.
 *
 * Sheets use it to tell "the reader went back past me, close" from "the reader
 * changed a filter while I was open, stay" — both are popstate, and without the
 * key they are indistinguishable.
 */
export function currentKey() {
  return current;
}

/** Push a history entry without changing the address: how a sheet opens. */
export function pushEntry() {
  navigate(route.path, route.query, { keepScroll: true });
  return current;
}

/** Step back, if there is anywhere to step back to. */
export function back(fallback = '/') {
  if (window.history.length > 1) window.history.back();
  else navigate(fallback);
}

/** Intercept in-app links so they do not reload the whole document. */
export function link(node) {
  function onClick(event) {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const href = node.getAttribute('href');
    if (!href || !href.startsWith('/')) return;
    event.preventDefault();
    const [path, search = ''] = href.split('?');
    navigate(path, Object.fromEntries(new URLSearchParams(search)));
  }
  node.addEventListener('click', onClick);
  return {
    destroy() {
      node.removeEventListener('click', onClick);
    },
  };
}
