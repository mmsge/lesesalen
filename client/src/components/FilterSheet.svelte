<script>
  /**
   * The filter sheet (3a): type, book, person.
   *
   * Every change is pushed to the URL as its own history entry, so the view is
   * shareable, survives a reload, and each filter is separately undoable with
   * back. That round trip is the point — paste a filtered address and you get
   * the same view — so the sheet never holds filter state of its own.
   *
   * Book chips carry a 22×33 swatch of the book's own cloth, because a list of
   * titles at chip size is unreadable and the colour is the thing people
   * actually recognise.
   */
  import Sheet from './Sheet.svelte';
  import { KINDS, toggleKind, toQuery, count, EMPTY, handleOf } from '../lib/filters.js';
  import { clothGradient } from '../lib/spine.js';
  import { setQuery } from '../lib/router.svelte.js';
  import { plain } from '../lib/sanitise.js';
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { filters, items = [], books = {}, shown = 0, total = 0, onclose } = $props();

  function update(next) {
    setQuery(toQuery(next));
  }

  /** Only books the collection actually holds posts about. */
  const shelf = $derived.by(() => {
    const wanted = new Map();
    for (const item of items) {
      const id = item.enrichment.bok;
      if (!id || wanted.has(id)) continue;
      const book = books[id] || item.book;
      if (book) wanted.set(id, book);
    }
    return [...wanted.entries()].sort((a, b) =>
      String(a[1].tittel || '').localeCompare(String(b[1].tittel || '')),
    );
  });

  const people = $derived.by(() => {
    const wanted = new Map();
    for (const item of items) {
      const handle = handleOf(item.core.account);
      if (!handle || wanted.has(handle)) continue;
      wanted.set(
        handle,
        plain(item.core.account?.display_name) || item.core.account?.username || handle,
      );
    }
    return [...wanted.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  });
</script>

<Sheet {onclose} label={t('filter.heading')} blur>
  <div class="head">
    <h2>{t('filter.heading')}</h2>
    <span class="of">
      {t('filter.showing', { shown: formatNumber(shown), total: formatNumber(total) })}
    </span>
  </div>

  <p class="label dim">{t('filter.kind')}</p>
  <div class="chips">
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
  </div>

  {#if shelf.length}
    <p class="label dim">{t('filter.book')}</p>
    <div class="chips">
      {#each shelf as [id, book] (id)}
        {@const on = filters.book === id}
        <button
          type="button"
          class="chip with-swatch"
          class:on
          aria-pressed={on}
          onclick={() => update({ ...filters, book: on ? null : id })}
        >
          <span class="swatch" aria-hidden="true" style:background={clothGradient(id)}></span>
          <span class="chip-text">{book.tittel || t('cover.unknown')}</span>
          {#if on}<span aria-hidden="true">×</span>{/if}
        </button>
      {/each}
    </div>
  {/if}

  {#if people.length}
    <p class="label dim">{t('filter.person')}</p>
    <div class="chips">
      {#each people as [handle, name] (handle)}
        {@const on = filters.person === handle}
        <button
          type="button"
          class="chip"
          class:on
          aria-pressed={on}
          onclick={() => update({ ...filters, person: on ? null : handle })}
        >
          {name}
        </button>
      {/each}
    </div>
  {/if}

  <p class="note">{t('filter.linkable')}</p>

  <div class="foot">
    <button type="button" class="reset" onclick={() => update(EMPTY)} disabled={!count(filters)}>
      {t('filter.clear')}
    </button>
    <button type="button" class="primary" onclick={() => onclose?.()}>
      {t('filter.apply', { n: formatNumber(shown) })}
    </button>
  </div>
</Sheet>

<style>
  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 18px;
  }

  h2 {
    margin: 0;
    font-size: 1.3rem;
    color: var(--paper-bright);
  }

  .of {
    font-size: 0.8rem;
    color: var(--paper-dim);
  }

  .label {
    margin-bottom: 10px;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 20px;
  }

  /* Every chip clears 44px, swatch or not. */
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    min-height: 44px;
    max-width: 100%;
    padding: 0 16px;
    background: none;
    border: 1px solid var(--rule);
    border-radius: 999px;
    color: var(--paper-dim);
    font-size: 0.9rem;
  }

  .chip.with-swatch {
    padding: 4px 14px 4px 6px;
    font-size: 0.88rem;
  }

  .chip.on {
    background: var(--brass);
    border-color: var(--brass);
    color: var(--ink);
    font-weight: 600;
  }

  .swatch {
    flex: none;
    width: 22px;
    height: 33px;
    border-radius: 1px;
  }

  .chip-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .note {
    margin: 0 0 16px;
    font-size: 0.82rem;
    color: var(--paper-dim);
  }

  .foot {
    display: flex;
    gap: 10px;
  }

  .reset {
    flex: none;
    min-height: 48px;
    padding: 0 18px;
    background: none;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    color: var(--paper-dim);
  }

  .reset:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .foot .primary {
    flex: 1;
    font-size: 1rem;
  }
</style>
