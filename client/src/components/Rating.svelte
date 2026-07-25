<script>
  /**
   * Ratings as filled and hollow marks in brass — never emoji stars.
   *
   * BookWyrm allows halves, so each mark is full, half or hollow. The three
   * states are classes rather than computed widths, which keeps every style in
   * the stylesheet where `style-src 'self'` wants it.
   */
  import { t } from '../lib/i18n.svelte.js';

  let { value = null, size = 'normal' } = $props();

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
</script>

{#if value !== null}
  <span class="rating" class:small={size === 'small'} title={t('card.ratingOf', { rating: value })}>
    <span class="visually-hidden">{t('card.ratingOf', { rating: value })}</span>
    {#each marks as mark, index (index)}
      <span class="mark {mark}" aria-hidden="true"></span>
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
    --mark-size: 0.85rem;
    position: relative;
    display: inline-block;
    width: var(--mark-size);
    height: var(--mark-size);
    /* A lozenge: a bookplate mark, not a star. */
    transform: rotate(45deg);
    border: 1px solid var(--brass);
    border-radius: 1px;
    overflow: hidden;
  }

  .small .mark {
    --mark-size: 0.6rem;
  }

  .mark.full {
    background: var(--brass);
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
