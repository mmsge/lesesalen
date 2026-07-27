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

/**
 * A translated sentence, split around its placeholders.
 *
 * Some sentences need one word set differently from the rest — a book title in
 * `--paper-prose` inside a `--paper-dim` line — and the only alternatives are
 * putting markup in the catalogue or assembling the sentence from fragments.
 * Both are worse: the fragments break the moment two languages disagree about
 * word order, which is exactly why `status.stale` is stored whole.
 *
 * Returns `[{ text }, { slot, value }, …]` in the order the active language
 * puts them, so the caller decides how each part is rendered.
 */
export function tParts(key, vars = {}) {
  const template = t(key);
  const out = [];
  let index = 0;
  for (const match of template.matchAll(/\{(\w+)\}/g)) {
    if (match.index > index) out.push({ text: template.slice(index, match.index) });
    const name = match[1];
    if (Object.prototype.hasOwnProperty.call(vars, name)) {
      out.push({ slot: name, value: String(vars[name]) });
    } else {
      out.push({ text: match[0] });
    }
    index = match.index + match[0].length;
  }
  if (index < template.length) out.push({ text: template.slice(index) });
  return out;
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

/** The month a date fell in, for "sidan mars". Day granularity is not the point. */
export function formatMonth(value) {
  if (!value) return '';
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(i18n.lang === 'en' ? 'en-GB' : 'nn-NO', {
    month: 'long',
  }).format(date);
}

/**
 * How old a post is, as a bare duration: "3 t", "1 d", "4 md".
 *
 * Bare on purpose. The feed byline wraps it in "{age} sidan" / "{age} ago", and
 * the reading-status line uses it alone — so this must not carry "ago" of its
 * own, or the byline reads "3 t sidan sidan".
 *
 * `Intl.RelativeTimeFormat` always includes the "ago", and narrow
 * `Intl.NumberFormat` units collapse minutes and months to the same "3m" in
 * both languages. Hence the suffixes in the catalogues: they are short enough
 * to be part of the design and different enough to be read.
 */
export function formatAge(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  const units = [
    ['year', 31536000],
    ['month', 2592000],
    ['week', 604800],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ];
  for (const [unit, size] of units) {
    if (seconds >= size) return t(`age.${unit}`, { n: formatNumber(Math.floor(seconds / size)) });
  }
  return t('age.now');
}
