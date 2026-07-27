/**
 * Composable filters: by kind, by person, by book.
 *
 * They live in the query string so a view is linkable and round-trips exactly:
 * paste `/?type=sitat,omtale&person=@aasta@bookwyrm.social` and you get the
 * same view back, on any device, with or without the collection that produced
 * it. That round trip is the acceptance criterion, so `parse` and `toQuery`
 * must stay each other's inverse.
 *
 * The book filter takes a BookWyrm work id, never a title: two editions of one
 * book share neither title casing nor punctuation, but they do share an id.
 */
import * as mastodon from './mastodon.js';

export const KINDS = ['omtale', 'vurdering', 'kommentar', 'sitat', 'lesestatus'];

/** `@x@host` and `x@host` are the same person; the `@` is decoration. */
function bareHandle(value) {
  return String(value || '').trim().replace(/^@/, '');
}

export function parse(query) {
  // `slag` was the old name for the same parameter. Links people have already
  // bookmarked keep working.
  const kinds = String(query.type ?? query.slag ?? '')
    .split(',')
    .map((value) => value.trim())
    .filter((value) => KINDS.includes(value));
  return {
    kinds,
    person: bareHandle(query.person) || null,
    book: String(query.bok || '').trim() || null,
  };
}

export function toQuery(filters) {
  return {
    type: filters.kinds.length ? filters.kinds.join(',') : '',
    // Written back with the `@` the route table specifies.
    person: filters.person ? `@${bareHandle(filters.person)}` : '',
    bok: filters.book || '',
    slag: '', // clears the legacy parameter rather than carrying it forward
  };
}

export const EMPTY = { kinds: [], person: null, book: null };

export function isEmpty(filters) {
  return !filters.kinds.length && !filters.person && !filters.book;
}

/** How many filters are on — the number the filter tab shows (4e). */
export function count(filters) {
  return filters.kinds.length + (filters.person ? 1 : 0) + (filters.book ? 1 : 0);
}

/** The stable handle for a person: `user@domain`, even for local accounts. */
export function handleOf(account) {
  if (!account) return '';
  if (account.acct && account.acct.includes('@')) return account.acct;
  const domain = mastodon.accountDomain(account);
  return domain ? `${account.acct || account.username}@${domain}` : account.acct || '';
}

export function apply(items, filters) {
  if (isEmpty(filters)) return items;
  return items.filter((item) => {
    if (filters.kinds.length && !filters.kinds.includes(item.enrichment.slag)) return false;
    if (filters.person && handleOf(item.core.account) !== bareHandle(filters.person)) return false;
    if (filters.book && item.enrichment.bok !== filters.book) return false;
    return true;
  });
}

export function toggleKind(filters, kind) {
  const kinds = filters.kinds.includes(kind)
    ? filters.kinds.filter((value) => value !== kind)
    : [...filters.kinds, kind];
  return { ...filters, kinds };
}
