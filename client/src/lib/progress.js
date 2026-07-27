/**
 * The one predicate that decides whether a post has reading progress.
 *
 * BookWyrm's `position` only means a page number when `positionMode` is `PG`,
 * and the field is absent from most posts — so "side 88" is rare, and the
 * comment card without a progress line is the norm, not the exception.
 *
 * Everything that shows progress, and everything that changes because progress
 * exists (the comment card's brass left border), asks this function. Never
 * derive it from anything else: not from the page count, not from a reading
 * status, not from `endposition`, and never invent one to fill a layout.
 *
 * `posisjonsmodus` is the server's name for `positionMode`, and `'side'` is its
 * name for `PG` (app/enrich.py). It is `null` when the origin object did not
 * say, which is exactly the case this guard exists for.
 */
export function hasProgress(enrichment) {
  if (!enrichment) return false;
  const position = enrichment.posisjon;
  return typeof position === 'number' && enrichment.posisjonsmodus === 'side';
}

/** The fraction read, or null when the edition's page count is unknown. */
export function fractionOf(position, pages) {
  if (typeof position !== 'number' || typeof pages !== 'number' || pages <= 0) return null;
  return Math.max(0, Math.min(1, position / pages));
}
