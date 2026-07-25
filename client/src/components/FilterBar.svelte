<script>
  /**
   * Composable filter chips in a sticky header.
   *
   * Filter state lives in the URL, so a view is linkable and survives a reload.
   */
  import { KINDS, isEmpty, toggleKind, toQuery } from '../lib/filters.js';
  import { setQuery } from '../lib/router.svelte.js';
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { filters, shown = 0, total = 0, books = {} } = $props();

  function update(next) {
    setQuery(toQuery(next));
  }

  const bookTitle = $derived(filters.book ? books[filters.book]?.tittel || filters.book : null);
</script>

<div class="bar">
  <div class="row">
    <span class="label">{t('filter.kind')}</span>
    {#each KINDS as kind (kind)}
      <button
        type="button"
        class="chip"
        class:on={filters.kinds.includes(kind)}
        aria-pressed={filters.kinds.includes(kind)}
        onclick={() => update(toggleKind(filters, kind))}
      >
        {t(`kind.${kind}`)}
      </button>
    {/each}

    {#if filters.person}
      <button
        type="button"
        class="chip on removable"
        onclick={() => update({ ...filters, person: null })}
        title={t('filter.clearOne', { label: filters.person })}
      >
        {filters.person} <span aria-hidden="true">×</span>
      </button>
    {/if}

    {#if filters.book}
      <button
        type="button"
        class="chip on removable"
        onclick={() => update({ ...filters, book: null })}
        title={t('filter.clearOne', { label: bookTitle })}
      >
        {bookTitle} <span aria-hidden="true">×</span>
      </button>
    {/if}

    {#if !isEmpty(filters)}
      <button type="button" class="clear" onclick={() => update({ kinds: [], person: null, book: null })}>
        {t('filter.clear')}
      </button>
    {/if}
  </div>

  {#if !isEmpty(filters)}
    <p class="count">
      {t('filter.showing', { shown: formatNumber(shown), total: formatNumber(total) })}
      <span class="hint">{t('filter.linkable')}</span>
    </p>
  {/if}
</div>

<style>
  .bar {
    position: sticky;
    top: 0;
    z-index: 5;
    background: color-mix(in srgb, var(--ink-900) 92%, transparent);
    backdrop-filter: blur(6px);
    border-bottom: 1px solid var(--rule);
    padding: 0.6rem 0;
    margin-bottom: 1.25rem;
  }

  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4em;
  }

  .label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--paper-dim);
    margin-right: 0.2em;
  }

  .chip {
    background: none;
    border: 1px solid var(--rule);
    border-radius: 999px;
    padding: 0.15em 0.75em;
    font-size: 0.82rem;
    color: var(--paper-dim);
  }

  .chip:hover {
    color: var(--paper);
    border-color: var(--paper-dim);
  }

  .chip.on {
    color: var(--ink-900);
    background: var(--brass);
    border-color: var(--brass);
    font-weight: 600;
  }

  .removable {
    max-width: 18rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .clear {
    background: none;
    border: 0;
    color: var(--paper-dim);
    font-size: 0.82rem;
    text-decoration: underline;
    text-underline-offset: 0.15em;
  }

  .clear:hover {
    color: var(--paper);
  }

  .count {
    margin: 0.5em 0 0;
    font-size: 0.8rem;
    color: var(--paper-dim);
  }

  .hint {
    margin-left: 0.6em;
    opacity: 0.75;
  }
</style>
