<script>
  /**
   * "side 143 av 320" plus a thin brass rule — and nothing at all otherwise.
   *
   * This renders only when the post carries a real page position: `posisjon`
   * non-null AND `posisjonsmodus === 'side'` (BookWyrm's `PG`). See
   * lib/progress.js. The reader can ask for percentages in Settings, and that
   * is still computed from the page number and the edition's page count — never
   * from anything else, and never when there is no page number to start with.
   */
  import { hasProgress, fractionOf } from '../lib/progress.js';
  import { prefs } from '../lib/prefs.svelte.js';
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { enrichment = null, pages = null } = $props();

  const show = $derived(hasProgress(enrichment));
  const position = $derived(show ? enrichment.posisjon : null);
  const fraction = $derived(show ? fractionOf(position, pages) : null);

  const label = $derived.by(() => {
    if (!show) return '';
    // Percentages need a page count. Without one the page number stands alone,
    // rather than a percentage of nothing.
    if (prefs.percent && fraction !== null) {
      return t('card.percent', { percent: formatNumber(Math.round(fraction * 100)) });
    }
    return pages
      ? t('card.page', { page: formatNumber(position), pages: formatNumber(pages) })
      : t('card.pageNoTotal', { page: formatNumber(position) });
  });
</script>

{#if show}
  <p class="progress">
    {#if fraction !== null}
      <span class="bar" aria-hidden="true">
        <span class="fill" style:width={`${(fraction * 100).toFixed(1)}%`}></span>
      </span>
    {/if}
    <span class="figure">{label}</span>
  </p>
{/if}

<style>
  .progress {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 8px 0 0;
    font-size: 0.8rem;
    color: var(--paper-dim);
  }

  .bar {
    flex: 1 1 auto;
    max-width: 84px;
    height: 2px;
    background: var(--rule);
    border-radius: 1px;
    overflow: hidden;
  }

  .fill {
    display: block;
    height: 100%;
    background: var(--brass);
  }

  .figure {
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
</style>
