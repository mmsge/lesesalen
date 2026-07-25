<script>
  /**
   * A book cover. The loudest thing on the page, by design.
   *
   * While the JPEG loads, the block is painted with the average colour taken
   * from the BlurHash, so a feed of covers settles rather than flashing.
   *
   * Covers are always served from our own origin: readers never hit BookWyrm
   * instances for images, so no reader IP leaks outward.
   */
  import { averageColour } from '../lib/colour.js';
  import { t } from '../lib/i18n.svelte.js';

  let { book = null, size = 'normal' } = $props();

  let loaded = $state(false);

  const tint = $derived(book?.blurhash ? averageColour(book.blurhash) : null);
  const title = $derived(book?.tittel || t('card.unknownBook'));
</script>

<div
  class="cover {size}"
  class:empty={!book?.omslag}
  style:background-color={tint || 'var(--ink-700)'}
>
  {#if book?.omslag}
    <img
      src={book.omslag}
      alt={t('card.coverAlt', { title })}
      loading="lazy"
      decoding="async"
      class:loaded
      onload={() => (loaded = true)}
    />
  {:else}
    <span class="placeholder" aria-hidden="true">{title.slice(0, 1)}</span>
    <span class="visually-hidden">{t('card.noCover')}</span>
  {/if}
</div>

<style>
  .cover {
    position: relative;
    flex: none;
    aspect-ratio: 2 / 3;
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow:
      0 1px 0 rgba(237, 228, 211, 0.06) inset,
      0 8px 24px rgba(0, 0, 0, 0.45);
  }

  .cover.small {
    width: 3rem;
  }

  .cover.normal {
    width: 7.5rem;
  }

  .cover.large {
    width: 10.5rem;
  }

  img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0;
  }

  img.loaded {
    opacity: 1;
  }

  @media (prefers-reduced-motion: no-preference) {
    img {
      transition: opacity 240ms ease-out;
    }
  }

  .placeholder {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    font-family: var(--serif);
    font-size: 2rem;
    color: var(--paper-dim);
    opacity: 0.5;
  }

  .cover.small .placeholder {
    font-size: 1.1rem;
  }
</style>
