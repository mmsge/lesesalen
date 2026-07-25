/**
 * Nynorsk default, English second.
 *
 * JSON catalogues rather than an i18n framework — the string count is small and
 * a framework would be more machinery than the problem deserves. The chosen
 * language is kept in localStorage and reflected in `<html lang>`, which the
 * server also sets from Accept-Language for the first paint.
 */
import nn from './locales/nn.json';
import en from './locales/en.json';

const CATALOGUES = { nn, en };
const KEY = 'lesesalen.sprak';

function initial() {
  try {
    const stored = window.localStorage.getItem(KEY);
    if (stored === 'nn' || stored === 'en') return stored;
  } catch {
    /* storage unavailable */
  }
  // The server already negotiated one and stamped it on <html lang>; agreeing
  // with it avoids a flash of the wrong language.
  const marked = document.documentElement.lang;
  if (marked === 'en' || marked === 'nn') return marked;
  const preferred = (navigator.languages || [navigator.language || 'nn'])[0] || 'nn';
  return preferred.toLowerCase().startsWith('en') ? 'en' : 'nn';
}

export const i18n = $state({ lang: initial() });

export function setLanguage(lang) {
  if (lang !== 'nn' && lang !== 'en') return;
  i18n.lang = lang;
  document.documentElement.lang = lang;
  try {
    window.localStorage.setItem(KEY, lang);
  } catch {
    /* not fatal */
  }
}

function lookup(catalogue, key) {
  return key.split('.').reduce((node, part) => (node == null ? undefined : node[part]), catalogue);
}

/**
 * Translate. `t('card.boostedBy', { name })` fills {name} placeholders.
 *
 * Reading `i18n.lang` here is what makes every call site re-render when the
 * language changes — do not cache the catalogue outside this function.
 */
export function t(key, vars) {
  const value = lookup(CATALOGUES[i18n.lang], key) ?? lookup(CATALOGUES.nn, key) ?? key;
  if (typeof value !== 'string' || !vars) return value;
  return value.replace(/\{(\w+)\}/g, (whole, name) =>
    Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : whole,
  );
}

/** Whole sub-trees, for the prose on the About and Privacy pages. */
export function block(key) {
  return lookup(CATALOGUES[i18n.lang], key) ?? lookup(CATALOGUES.nn, key) ?? [];
}

export function formatNumber(value) {
  return new Intl.NumberFormat(i18n.lang === 'en' ? 'en-GB' : 'nn-NO').format(value);
}

export function formatDate(value) {
  if (!value) return '';
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(i18n.lang === 'en' ? 'en-GB' : 'nn-NO', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date);
}

/** Relative time for post ages: "3 t", "2 d". */
export function formatAge(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat(i18n.lang === 'en' ? 'en-GB' : 'nn-NO', {
    numeric: 'auto',
    style: 'narrow',
  });
  const units = [
    ['year', 31536000],
    ['month', 2592000],
    ['week', 604800],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ];
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  }
  return formatter.format(Math.round(seconds), 'second');
}
