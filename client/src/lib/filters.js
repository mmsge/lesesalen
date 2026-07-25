/**
 * Composable filters: by kind, by person, by book.
 *
 * They live in the query string so a view is linkable — `?slag=sitat,omtale`
 * is a bookmarkable "quotations and reviews".
 */
import * as mastodon from './mastodon.js';

export const KINDS = ['omtale', 'vurdering', 'kommentar', 'sitat', 'lesestatus'];

export function parse(query) {
  return {
    kinds: String(query.slag || '')
      .split(',')
      .map((value) => value.trim())
      .filter((value) => KINDS.includes(value)),
    person: String(query.person || '').trim() || null,
    book: String(query.bok || '').trim() || null,
  };
}

export function toQuery(filters) {
  return {
    slag: filters.kinds.length ? filters.kinds.join(',') : '',
    person: filters.person || '',
    bok: filters.book || '',
  };
}

export function isEmpty(filters) {
  return !filters.kinds.length && !filters.person && !filters.book;
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
    if (filters.person && handleOf(item.core.account) !== filters.person) return false;
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
