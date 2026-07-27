/**
 * What a book looks like when we have no cover for it.
 *
 * A synthesised jacket has to be *the same jacket* every time: the same book
 * must stand out at the same width, in the same cloth, on this reader's phone
 * today and on their laptop next month. So everything here is a pure function
 * of the BookWyrm work id and nothing else — not of load order, not of
 * `Math.random`, not of a counter.
 *
 * The prototype summed character codes, which collides constantly (an anagram
 * of an id is the same book) and clusters, because ids from one instance share
 * a long prefix. FNV-1a spreads them properly and is four lines.
 *
 * The cloth pairs are book-binding colours rather than palette tokens: they are
 * generated cover *art*, the same kind of value as a BlurHash, and they never
 * appear as UI chrome. That is why they live in JavaScript and not in app.css.
 */

/** [front, back] of each binding cloth, as they gradient from top-left. */
export const CLOTHS = [
  ['#7a5340', '#3f2418'],
  ['#41616e', '#1c2b32'],
  ['#3f4a35', '#232c1c'],
  ['#6b4a58', '#2f1d26'],
];

/** FNV-1a, 32-bit. Deterministic, dependency-free, well spread over short ids. */
export function hash(id) {
  let value = 0x811c9dc5;
  const text = String(id ?? '');
  for (let index = 0; index < text.length; index += 1) {
    value ^= text.charCodeAt(index);
    // The FNV prime, multiplied without overflowing the float mantissa.
    value = Math.imul(value, 0x01000193) >>> 0;
  }
  return value >>> 0;
}

/**
 * The cloth for a book. Different bit fields of the one hash feed the different
 * properties, so width and colour vary independently rather than in lockstep.
 */
export function clothOf(id) {
  return CLOTHS[hash(id) % CLOTHS.length];
}

/** `linear-gradient(...)` for a jacket or spine of this book. */
export function clothGradient(id) {
  const [front, back] = clothOf(id);
  return `linear-gradient(155deg, ${front}, ${back})`;
}

/**
 * A spine standing on the shelf strip: 22–55px wide, 74–94px tall inside the
 * 100px strip. Both are read off the hash, so a shelf has a real skyline and
 * the same book keeps its silhouette.
 */
export function spineOf(id) {
  const seed = hash(id);
  return {
    width: 22 + ((seed >>> 4) % 4) * 11,
    height: 74 + ((seed >>> 11) % 5) * 5,
    gradient: clothGradient(id),
  };
}

/**
 * Jacket internals, scaled to the cover width (§Covers).
 *
 * The gutter is 7.5% of the width, the title is roughly w/145 rem clamped to
 * 0.62–1.15rem, and below ~60px there is no room for type at all — that is a
 * spine, and it gets the cloth and the gutter and nothing else.
 */
export function jacketOf(id, width) {
  return {
    gradient: clothGradient(id),
    gutter: Math.max(5, Math.round(width * 0.075)),
    titleSize: Math.max(0.62, Math.min(1.15, width / 145)),
    top: Math.round(width * 0.16),
    lettered: width >= 60,
  };
}

/**
 * The cover shadow, scaled with the cover: `0 {w*0.18}px {w*0.3}px` plus the
 * inset highlight that makes it read as lit rather than pasted on.
 */
export function coverShadow(width) {
  return (
    `0 ${Math.round(width * 0.18)}px ${Math.round(width * 0.3)}px rgba(0, 0, 0, 0.72),` +
    ' 0 1px 0 rgba(246, 239, 225, 0.12) inset'
  );
}
