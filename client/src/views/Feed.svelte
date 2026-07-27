<script>
  /**
   * The reading room (2a): the outboxes of the BookWyrm accounts the reader
   * follows, laid out as five kinds of card separated by lit shelf rails.
   *
   * Rails go **between** posts — never above the first, never below the last,
   * except the one that closes the feed before the tail block.
   *
   * Nothing here is a blocking screen. A cold sweep is a hairline under the
   * header; hosts that failed are a notice above the shelf; an expired session
   * is a panel that leaves the collection alone; offline is a grey dot. In every
   * one of those states the shelf below still shows what arrived.
   */
  import Card from '../components/Card.svelte';
  import FeedHeader from '../components/FeedHeader.svelte';
  import ShelfStrip from '../components/ShelfStrip.svelte';
  import Skeleton from '../components/Skeleton.svelte';
  import SweepNotice from '../components/SweepNotice.svelte';
  import Tail from '../components/Tail.svelte';
  import QueuedReply from '../components/QueuedReply.svelte';
  import { feed, load, restore, resweep, reach } from '../lib/collection.svelte.js';
  import { inferQuiet } from '../lib/stale.js';
  import { apply, count, toQuery, isEmpty, handleOf } from '../lib/filters.js';
  import { queue } from '../lib/queue.svelte.js';
  import { net } from '../lib/net.svelte.js';
  import { setQuery, navigate } from '../lib/router.svelte.js';
  import { pullToRefresh, PULL_THRESHOLD } from '../lib/pull.js';
  import { plain } from '../lib/sanitise.js';
  import { i18n, t, formatNumber } from '../lib/i18n.svelte.js';

  let {
    account,
    filters,
    onopen,
    onperson,
    onbook,
    onreply,
  } = $props();

  let sentinel = $state(null);
  let pull = $state(0);
  let started = false;

  // Books somebody started and has said nothing about since. Derived here, in
  // this browser, from this reader's own collection — and labelled as derived
  // wherever it is drawn (lib/stale.js).
  const all = $derived.by(() => {
    const inferred = inferQuiet(feed.items);
    if (!inferred.length) return feed.items;
    return [...feed.items, ...inferred].sort(
      (a, b) => Date.parse(b.core.created_at) - Date.parse(a.core.created_at),
    );
  });

  const visible = $derived(apply(all, filters));
  const active = $derived(count(filters));
  const sweeping = $derived(feed.loading && (feed.phase === 'breidde' || feed.phase === 'fylgje' || feed.phase === 'instansar'));
  const deepening = $derived(feed.loading && feed.phase === 'djupn');
  const noBookwyrm = $derived(!feed.shelves && !feed.loading && feed.followCount > 0);

  /** The books currently on the shelf strip: the ones the top of the feed is about. */
  const onShelf = $derived.by(() => {
    const wanted = new Map();
    for (const item of visible) {
      const id = item.enrichment.bok;
      const book = item.book;
      if (!id || !book || wanted.has(id)) continue;
      wanted.set(id, book);
      if (wanted.size >= 12) break;
    }
    return [...wanted.values()];
  });

  // Read the browser's own collection before touching the network, then sweep
  // for whatever is new.
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

  function refresh() {
    resweep();
    load(account);
  }

  /** What the filter found nothing of, in the reader's own words (4e). */
  const missing = $derived.by(() => {
    if (visible.length || !active) return null;
    const who = filters.person
      ? plain(
          all.find((item) => handleOf(item.core.account) === filters.person)?.core.account
            ?.display_name,
        ) || filters.person
      : null;
    const theirs = filters.person
      ? all.filter((item) => handleOf(item.core.account) === filters.person)
      : all;
    const kind = filters.kinds.length ? filters.kinds[0] : null;
    return {
      who,
      kind: kind ? t(`kind.${kind}`).toLocaleLowerCase(i18n.lang === 'en' ? 'en' : 'nn') : null,
      total: theirs.length,
    };
  });
</script>

<div
  class="feed"
  use:pullToRefresh={{
    enabled: !feed.loading && net.online,
    onmove: (distance) => (pull = distance),
    onrelease: refresh,
  }}
>
  {#if pull > 0}
    <div class="pull" style:height={`${pull}px`}>
      <span>{pull > PULL_THRESHOLD ? t('pull.release') : t('pull.hint')}</span>
    </div>
  {/if}

  <FeedHeader
    shelves={feed.shelves}
    reached={feed.failures.length ? feed.shelves - feed.failures.length : 0}
    {sweeping}
    expired={feed.expired}
    offline={!net.online}
  />

  <SweepNotice
    {sweeping}
    done={feed.swept}
    total={feed.sweeping || feed.shelves}
    failures={feed.failures}
    unreadable={feed.unreadable}
    onretry={refresh}
  />

  {#if feed.expired}
    <div class="expired">
      <p class="label heading">{t('expired.heading')}</p>
      <p class="says">{t('expired.body', { domain: account?.domain || '' })}</p>
      <button type="button" class="primary" onclick={() => navigate('/logg-inn')}>
        {t('expired.again')}
      </button>
    </div>
  {/if}

  <QueuedReply drafts={queue.items} onedit={(draft) => onreply?.({ uri: draft.uri })} />

  {#if active}
    <div class="chips">
      {#each filters.kinds as kind (kind)}
        <button
          type="button"
          class="chip"
          onclick={() =>
            setQuery(toQuery({ ...filters, kinds: filters.kinds.filter((k) => k !== kind) }))}
        >
          {t(`kind.${kind}`)} <span aria-hidden="true">×</span>
          <span class="visually-hidden">{t('filter.clearOne', { label: t(`kind.${kind}`) })}</span>
        </button>
      {/each}
      {#if filters.book}
        <button type="button" class="chip" onclick={() => setQuery(toQuery({ ...filters, book: null }))}>
          {feed.books[filters.book]?.tittel || t('cover.unknown')} <span aria-hidden="true">×</span>
        </button>
      {/if}
      {#if filters.person}
        <button type="button" class="chip" onclick={() => setQuery(toQuery({ ...filters, person: null }))}>
          {filters.person} <span aria-hidden="true">×</span>
        </button>
      {/if}
    </div>
  {/if}

  {#if noBookwyrm}
    <!-- 4a: an empty shelf is not a failure, so the tone is explanatory. -->
    <ShelfStrip empty={4} dim />
    <div class="empty">
      <h2>{t('empty.noBookwyrm')}</h2>
      <p>{t('empty.noBookwyrmBody', { n: formatNumber(feed.followCount) })}</p>
      <div class="choices">
        <a class="primary" href="https://bookwyrm.social/directory" rel="noopener noreferrer" target="_blank">
          {t('empty.findPeople')}
        </a>
        <button type="button" class="secondary" onclick={refresh}>{t('empty.recheck')}</button>
      </div>
      <p class="note">{t('empty.findPeopleHelp')}</p>
    </div>
  {:else}
    {#if !active && onShelf.length}
      <ShelfStrip books={onShelf} label={t('shelf.now')} {onbook} />
    {:else if !active && (sweeping || onShelf.length === 0)}
      <ShelfStrip empty={5} dim />
    {/if}

    {#if missing}
      <!-- 4e: say what does exist, and offer the two ways out. -->
      <div class="empty">
        <h2>
          {missing.who && missing.kind
            ? t('empty.noMatchPerson', { who: missing.who, kind: missing.kind })
            : t('empty.noMatch')}
        </h2>
        <p>{t('empty.noMatchBody', { n: formatNumber(missing.total) })}</p>
        <div class="choices">
          {#if filters.person}
            <button
              type="button"
              class="primary"
              onclick={() => setQuery(toQuery({ ...filters, kinds: [], book: null }))}
            >
              {t('empty.showAllFrom', { who: missing.who, n: formatNumber(missing.total) })}
            </button>
          {/if}
          <button
            type="button"
            class="secondary"
            onclick={() => setQuery(toQuery({ ...filters, person: null }))}
          >
            {t('empty.showFromEveryone')}
          </button>
        </div>
      </div>
    {:else}
      {#each visible as item, index (item.core.uri)}
        <div class="card-slot">
          <Card {item} {account} {onopen} {onperson} {onbook} {onreply} />
        </div>
        {#if index < visible.length - 1}<div class="rail"></div>{/if}
      {/each}

      {#if sweeping && visible.length < 3}
        {#if visible.length}<div class="rail"></div>{/if}
        <Skeleton />
      {/if}

      {#if !visible.length && !sweeping && isEmpty(filters) && feed.shelves}
        <div class="empty">
          <h2>{t('feed.empty')}</h2>
          <p>{t('feed.emptyDetail')}</p>
        </div>
      {/if}
    {/if}

    {#if !sweeping && !missing && visible.length}
      <div bind:this={sentinel} class="sentinel" aria-hidden="true"></div>
      <Tail
        posts={visible.length}
        reach={reach()}
        loading={deepening}
        exhausted={feed.exhausted}
        shelves={feed.shelves}
        disabled={!net.online || feed.expired}
        onmore={() => load(account)}
      />
    {/if}
  {/if}
</div>

<style>
  .feed {
    /* Clear of the fixed tab bar at the bottom. */
    padding-bottom: calc(var(--tabbar) + var(--safe-bottom));
  }

  .pull {
    display: grid;
    place-items: center;
    overflow: hidden;
    font-size: 0.78rem;
    color: var(--paper-dim);
  }

  .card-slot {
    width: min(100%, var(--column));
    margin-inline: auto;
  }

  /* From 44rem a rail stops being a wall and becomes a shelf in a room (4m). */
  @media (min-width: 44rem) {
    .rail {
      width: min(100% - 2.5rem, var(--column));
      margin-inline: auto;
      box-shadow: 0 10px 24px rgba(0, 0, 0, 0.55);
    }
  }

  .expired {
    width: min(100% - 40px, var(--column));
    margin: 0 auto 8px;
    padding: 14px 16px;
    background: var(--panel);
    border: 1px solid var(--rule);
    border-left: 2px solid var(--warn-rule);
    border-radius: var(--radius);
  }

  .heading {
    margin-bottom: 6px;
    color: var(--warn);
    letter-spacing: 0.16em;
  }

  .says {
    margin: 0 0 14px;
    font-size: 0.95rem;
    color: var(--paper);
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    width: min(100% - 40px, var(--column));
    margin: 0 auto 14px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-height: 44px;
    padding: 0 14px;
    background: var(--brass);
    border: 1px solid var(--brass);
    border-radius: 999px;
    color: var(--ink);
    font-size: 0.85rem;
    font-weight: 600;
  }

  .empty {
    width: min(100% - 44px, var(--column));
    margin-inline: auto;
    padding: 26px 0 24px;
  }

  .empty h2 {
    font-size: 1.45rem;
    line-height: 1.2;
    margin: 0 0 10px;
    color: var(--paper-bright);
  }

  .empty p {
    margin: 0 0 16px;
    color: var(--paper-dim);
  }

  .choices {
    display: grid;
    gap: 10px;
  }

  .choices .primary {
    text-decoration: none;
  }

  .note {
    margin: 16px 0 0;
    font-size: 0.85rem;
    color: var(--paper-dim);
  }

  .sentinel {
    height: 1px;
  }
</style>
