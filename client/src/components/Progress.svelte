<script>
  /** "side 143 av 400" plus a thin rule, when a post says where the reader is. */
  import { t } from '../lib/i18n.svelte.js';

  let { position = null, mode = 'side', pages = null } = $props();

  const fraction = $derived(
    position === null
      ? null
      : mode === 'prosent'
        ? Math.max(0, Math.min(1, position / 100))
        : pages
          ? Math.max(0, Math.min(1, position / pages))
          : null,
  );

  const label = $derived(
    position === null
      ? ''
      : mode === 'prosent'
        ? t('card.percent', { percent: position })
        : pages
          ? t('card.page', { page: position, pages })
          : t('card.pageNoTotal', { page: position }),
  );
</script>

{#if position !== null}
  <p class="progress">
    {#if fraction !== null}
      <span class="bar" aria-hidden="true">
        <span class="fill" style:width={`${(fraction * 100).toFixed(1)}%`}></span>
      </span>
    {/if}
    <span class="label">{label}</span>
  </p>
{/if}

<style>
  .progress {
    display: flex;
    align-items: center;
    gap: 0.6em;
    margin: 0.6em 0 0;
    font-size: 0.85rem;
    color: var(--paper-dim);
  }

  .bar {
    flex: 1 1 6rem;
    max-width: 10rem;
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

  .label {
    font-variant-numeric: tabular-nums;
  }
</style>
