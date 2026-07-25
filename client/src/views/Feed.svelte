<script>
  /**
   * The reading room itself: filters, cards, infinite scroll, and the two
   * answers to a sparse timeline (deeper paging, and an explicit gather).
   */
  import Card from '../components/Card.svelte';
  import Composer from '../components/Composer.svelte';
  import FilterBar from '../components/FilterBar.svelte';
  import { feed, loadMore, gather } from '../lib/feed.svelte.js';
  import { apply, handleOf, parse, toQuery } from '../lib/filters.js';
  import { navigate, route, setQuery } from '../lib/router.svelte.js';
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { account } = $props();

  let replyingTo = $state(null);
  let sentinel = $state(null);

  const filters = $derived(parse(route.query));
  const visible = $derived(apply(feed.items, filters));

  $effect(() => {
    if (!feed.items.length && !feed.loading) loadMore(account);
  });

  // Infinite scroll. An observer rather than a scroll handler, so it costs
  // nothing while the reader is reading.
  $effect(() => {
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) loadMore(account);
      },
      { rootMargin: '600px' },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
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
    {feed.digging ? t('feed.searchingBack') : t('feed.loading')}
    {#if feed.digging}<span class="detail">{t('feed.searchingBackDetail')}</span>{/if}
  </p>
{:else if feed.error}
  <p class="notice bad">
    {t('feed.error')}
    <button type="button" onclick={() => loadMore(account)}>{t('feed.retry')}</button>
  </p>
{:else if !visible.length}
  <div class="empty">
    <p class="lead">{t('feed.empty')}</p>
    <p class="detail">{t('feed.emptyDetail')}</p>
  </div>
{/if}

{#if feed.gathering}
  <p class="notice">{t('feed.gathering', { count: formatNumber(feed.gathering) })}</p>
{/if}

<div class="tail">
  {#if !feed.exhausted}
    <div bind:this={sentinel} class="sentinel" aria-hidden="true"></div>
    <button type="button" class="more" onclick={() => loadMore(account)} disabled={feed.loading}>
      {t('feed.loadMore')}
    </button>
  {:else}
    <p class="notice">{t('feed.end')}</p>
  {/if}

  <div class="gather">
    <button type="button" onclick={() => gather(account)} disabled={Boolean(feed.gathering)}>
      {t('feed.gather')}
    </button>
    <p class="detail">{t('feed.gatherHelp')}</p>
  </div>
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
    gap: 2rem;
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

  .gather {
    border-top: 1px solid var(--rule);
    padding-top: 1.5rem;
    max-width: 32rem;
    display: grid;
    gap: 0.5em;
    justify-items: center;
  }

  .gather button {
    background: none;
    border: 1px solid var(--brass);
    border-radius: var(--radius);
    padding: 0.4em 1.2em;
    color: var(--brass);
  }

  .gather button:hover:not(:disabled) {
    background: var(--brass);
    color: var(--ink-900);
  }

  .gather button:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
