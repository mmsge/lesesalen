<script>
  /**
   * Ratings as filled and hollow lozenges in brass — never emoji stars.
   *
   * BookWyrm allows halves, so each mark is full, half or hollow. The row is a
   * single `role="img"` with the whole rating as its label ("4,5 av 5"), so a
   * screen reader hears the figure once instead of five unlabelled shapes.
   */
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { value = null, size = 0.7 } = $props();

  const marks = $derived(
    value === null
      ? []
      : Array.from({ length: 5 }, (_, index) => {
          const filled = value - index;
          if (filled >= 1) return 'full';
          if (filled >= 0.5) return 'half';
          return 'empty';
        }),
  );

  /** "4,5 av 5" in Nynorsk, "4.5 out of 5" in English — the locale decides. */
  const spoken = $derived(value === null ? '' : t('card.ratingOf', { rating: formatNumber(value) }));
</script>

{#if value !== null}
  <span class="rating" role="img" aria-label={spoken} style:--mark-size={`${size}rem`}>
    {#each marks as mark, index (index)}
      <span class="mark {mark}"></span>
    {/each}
  </span>
{/if}

<style>
  .rating {
    display: inline-flex;
    gap: 0.25em;
    align-items: center;
    line-height: 1;
  }

  .mark {
    position: relative;
    display: inline-block;
    width: var(--mark-size);
    height: var(--mark-size);
    /* A lozenge: a bookplate mark, not a star. */
    transform: rotate(45deg);
    border: 1px solid var(--rule);
    border-radius: 1px;
    overflow: hidden;
  }

  .mark.full {
    background: var(--brass);
    border-color: var(--brass);
  }

  .mark.half {
    border-color: var(--brass);
  }

  /* The half mark fills one triangle, which reads correctly once rotated. */
  .mark.half::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
      to top right,
      var(--brass) 0,
      var(--brass) 50%,
      transparent 50%,
      transparent 100%
    );
  }
</style>
