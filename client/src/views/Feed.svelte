<script>
  /**
   * The reading room itself: filters, cards, and the sweep over the shelves of
   * the BookWyrm accounts the reader follows (ADR 0008).
   *
   * The sweep is phased, and the progress line says which phase it is in, because
   * a first visit genuinely takes a while: one throttled outbox request per
   * account, plus a lookup for every book edition nobody has fetched before. On
   * later visits the collection is read out of the browser first and this is all
   * that is left to do (ADR 0009).
   */
  import Card from '../components/Card.svelte';
  import Composer from '../components/Composer.svelte';
  import FilterBar from '../components/FilterBar.svelte';
  import { feed, load, restore, depth } from '../lib/collection.svelte.js';
  import { apply, handleOf, parse, toQuery } from '../lib/filters.js';
  import { navigate, route, setQuery } from '../lib/router.svelte.js';
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { account } = $props();

  let replyingTo = $state(null);
  let sentinel = $state(null);
  let started = false;

  const filters = $derived(parse(route.query));
  const visible = $derived(apply(feed.items, filters));

  // Read the browser's own collection before touching the network, then sweep for
  // whatever is new.
  $effect(() => {
    if (started) return;
    started = true;
    (async () => {
      await restore();
      await load(account);
    })();
  });

  // Infinite scroll. An observer rather than a scroll handler, so it costs
  // nothing while the reader is reading.
  $effect(() => {
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) load(account);
      },
      { rootMargin: '600px' },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  });

  /** What the sweep is doing, in the reader's language. */
  const progress = $derived.by(() => {
    if (!feed.loading) return null;
    if (feed.phase === 'fylgje') return t('samling.reading');
    if (feed.phase === 'instansar') return t('samling.probing');
    if (feed.phase === 'breidde')
      return t('samling.sweeping', {
        done: formatNumber(feed.swept),
        total: formatNumber(feed.shelves),
      });
    if (feed.phase === 'djupn') {
      const { read, total } = depth();
      return t('samling.deepening', {
        done: formatNumber(read),
        total: formatNumber(Math.max(total, read)),
      });
    }
    return t('feed.loading');
  });

  function onperson(who) {
    navigate(`/lesar/${encodeURIComponent(handleOf(who))}`);
  }

  function onbook(bookId) {
    setQuery(toQuery({ ...filters, book: bookId }));
  }
</script>

<FilterBar {filters} shown={visible.length} total={feed.items.length} books={feed.books} />

{#if feed.expired}
  <p class="notice bad">{t('feed.sessionExpired')}</p>
{/if}

{#if replyingTo}
  <Composer item={replyingTo} {account} onclose={() => (replyingTo = null)} />
{/if}

<div class="column">
  {#each visible as item (item.core.uri)}
    <Card
      {item}
      {account}
      {onperson}
      {onbook}
      onreply={(target) => (replyingTo = target)}
    />
  {/each}
</div>

{#if feed.loading}
  <p class="notice">
    {progress}
    {#if feed.phase === 'breidde'}<span class="detail">{t('samling.sweepingDetail')}</span>{/if}
  </p>
{:else if feed.error}
  <p class="notice bad">
    {t('feed.error')}
    <button type="button" onclick={() => load(account)}>{t('feed.retry')}</button>
  </p>
{:else if !visible.length}
  <div class="empty">
    <p class="lead">{feed.shelves ? t('feed.empty') : t('samling.noShelves')}</p>
    <p class="detail">{feed.shelves ? t('feed.emptyDetail') : t('samling.noShelvesDetail')}</p>
  </div>
{/if}

<div class="tail">
  {#if !feed.exhausted}
    <div bind:this={sentinel} class="sentinel" aria-hidden="true"></div>
    <button type="button" class="more" onclick={() => load(account)} disabled={feed.loading}>
      {t('samling.deepen')}
    </button>
    <p class="detail">{t('samling.deepenHelp')}</p>
  {:else}
    <p class="notice">{t('samling.end', { count: formatNumber(feed.shelves) })}</p>
  {/if}
</div>

<style>
  .column {
    display: grid;
    gap: 1.5rem;
  }

  .notice {
    margin: 1.5rem 0;
    color: var(--paper-dim);
    font-size: 0.9rem;
    display: grid;
    gap: 0.3em;
  }

  .notice.bad {
    color: var(--oxblood);
  }

  .notice button {
    justify-self: start;
    background: none;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 0.2em 0.7em;
    color: var(--paper);
    font-size: 0.85rem;
  }

  .detail {
    font-size: 0.85rem;
    color: var(--paper-dim);
    margin: 0;
  }

  .empty {
    margin: 3rem 0;
    text-align: center;
  }

  .empty .lead {
    font-family: var(--serif);
    font-size: var(--step-2);
    margin: 0 0 0.3em;
  }

  .tail {
    margin: 2.5rem 0 4rem;
    display: grid;
    gap: 0.75rem;
    justify-items: center;
    text-align: center;
  }

  .sentinel {
    height: 1px;
  }

  .more {
    background: none;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 0.4em 1.4em;
    color: var(--paper);
  }

  .more:hover:not(:disabled) {
    border-color: var(--brass);
    color: var(--brass);
  }

  .more:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .tail .detail {
    max-width: 32rem;
  }
</style>
