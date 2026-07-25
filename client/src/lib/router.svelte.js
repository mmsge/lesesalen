/**
 * A router small enough to read in one sitting.
 *
 * Filter state lives in the query string on purpose, so a view is linkable:
 * `/?slag=sitat&person=someone@example.social` is a shareable bookmark of
 * "quotations from this person".
 */
export const route = $state({
  path: window.location.pathname,
  query: Object.fromEntries(new URLSearchParams(window.location.search)),
});

function sync() {
  route.path = window.location.pathname;
  route.query = Object.fromEntries(new URLSearchParams(window.location.search));
}

window.addEventListener('popstate', sync);

export function navigate(path, query = {}, { replace = false } = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && value !== '') params.set(key, value);
  }
  const search = params.toString();
  const url = search ? `${path}?${search}` : path;
  if (replace) window.history.replaceState({}, '', url);
  else window.history.pushState({}, '', url);
  sync();
  window.scrollTo({ top: 0 });
}

/** Update the query string in place, keeping the current path. */
export function setQuery(query, { replace = true } = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && value !== '') params.set(key, value);
  }
  const search = params.toString();
  const url = search ? `${route.path}?${search}` : route.path;
  if (replace) window.history.replaceState({}, '', url);
  else window.history.pushState({}, '', url);
  sync();
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
