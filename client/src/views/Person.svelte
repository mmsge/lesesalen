<script>
  /**
   * One person's shelf, at its own address (5f).
   *
   * `/@mvrkws@bookwyrm.social` is a real, shareable route and it is **public** —
   * no session required. That is the point of the page, which is why the
   * copyable address sits above the fold rather than in a menu.
   *
   * It supersedes the old author view, and it is where the detail's "Hylla"
   * button and every byline in the feed lead — not to a person filter on the
   * feed, which is not a thing you can send anybody.
   *
   * The shelf comes from the same outbox walk as the feed, through
   * `/api/samling`, which carries no token and needs none.
   */
  import Card from '../components/Card.svelte';
  import Icon from '../components/Icon.svelte';
  import ShelfStrip from '../components/ShelfStrip.svelte';
  import * as mastodon from '../lib/mastodon.js';
  import { shelfOf } from '../lib/collection.svelte.js';
  import { plain } from '../lib/sanitise.js';
  import { show } from '../lib/toast.svelte.js';
  import { back } from '../lib/router.svelte.js';
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { handle, account = null, onopen, onperson, onbook, onreply } = $props();

  let items = $state([]);
  let who = $state(null);
  let loading = $state(true);
  let problem = $state(false);
  let copied = $state(false);
  let kind = $state('alle');

  $effect(() => {
    let cancelled = false;
    loading = true;
    problem = false;
    items = [];
    (async () => {
      try {
        // With a session the reader's own instance gives the authoritative
        // account; without one the handle is all there is, and shelfOf works
        // out the actor URI from it.
        let found = { acct: handle };
        if (account) {
          try {
            found = await mastodon.lookupAccount(account, handle);
          } catch {
            /* not federated here yet: fall back to the handle */
          }
        }
        if (cancelled) return;
        // The handle from the address is authoritative for *which* person this
        // page is about; the lookup only enriches it. An instance that answers
        // with something thinner must not leave the page pointing at nobody.
        who = { ...found, acct: found?.acct || handle };
        const shelf = await shelfOf(who, 3);
        if (!cancelled) items = shelf.items;
      } catch {
        if (!cancelled) problem = true;
      } finally {
        if (!cancelled) loading = false;
      }
    })();
    return () => {
      cancelled = true;
    };
  });

  const name = $derived(plain(who?.display_name) || who?.username || handle.split('@')[0]);
  const address = $derived(`${window.location.host}/@${handle}`);
  const books = $derived.by(() => {
    const wanted = new Map();
    for (const item of items) {
      const id = item.enrichment.bok;
      if (id && item.book && !wanted.has(id)) wanted.set(id, item.book);
    }
    return [...wanted.values()];
  });

  // Plural forms, not the singular kind labels: "Omtalar 31", not "Omtale 31".
  const COUNTS = [
    { id: 'alle', label: 'person.all' },
    { id: 'omtale', label: 'person.reviews' },
    { id: 'sitat', label: 'person.quotes' },
  ];

  const shown = $derived(
    kind === 'alle' ? items : items.filter((item) => item.enrichment.slag === kind),
  );

  async function copy() {
    try {
      await navigator.clipboard.writeText(`https://${address}`);
      copied = true;
      show('person.copied');
    } catch {
      show('person.copyFailed', 'warn');
    }
  }
</script>

<div class="person fades">
  <div class="nav">
    <button type="button" class="chev" aria-label={t('nav.back')} onclick={() => back()}>
      <Icon name="back" size={20} />
    </button>
    <span class="label-back">{t('nav.backToFeed')}</span>
  </div>

  <div class="head">
    <div class="identity">
      <span class="avatar" aria-hidden="true">{(name || '?').slice(0, 1)}</span>
      <div class="names">
        <h2>{name}</h2>
        <p class="handle">@{handle}</p>
        <p class="counts">
          {t('person.posts', { n: formatNumber(items.length) })} · {t('person.books', {
            n: formatNumber(books.length),
          })}
        </p>
      </div>
    </div>

    <div class="address">
      <span class="url">{address}</span>
      <button type="button" class="copy" aria-label={t('person.copyLink')} onclick={copy}>
        <Icon name={copied ? 'check' : 'copy'} size={18} />
      </button>
    </div>
    <p class="public">{t('person.publicNote')}</p>
  </div>

  {#if books.length}
    <ShelfStrip
      {books}
      label={`${t('shelf.all')} · ${t('person.books', { n: formatNumber(books.length) })}`}
      {onbook}
    />
  {/if}

  <div class="chips">
    {#each COUNTS as entry (entry.id)}
      {@const n = entry.id === 'alle' ? items.length : items.filter((i) => i.enrichment.slag === entry.id).length}
      <button
        type="button"
        class="chip"
        class:on={kind === entry.id}
        aria-pressed={kind === entry.id}
        onclick={() => (kind = entry.id)}
      >
        {t(entry.label)} {formatNumber(n)}
      </button>
    {/each}
  </div>

  {#if loading}
    <p class="notice">{t('person.loading')}</p>
  {:else if problem}
    <p class="notice">{t('error.generic')}</p>
  {:else if !shown.length}
    <p class="notice">{t('person.empty')}</p>
  {:else}
    {#each shown as item, index (item.core.uri)}
      <div class="card-slot">
        <Card {item} {account} {onopen} {onperson} {onbook} {onreply} />
      </div>
      {#if index < shown.length - 1}<div class="rail"></div>{/if}
    {/each}
  {/if}
</div>

<style>
  .person {
    padding-bottom: calc(var(--tabbar) + var(--safe-bottom));
  }

  .nav,
  .head,
  .chips,
  .card-slot,
  .notice {
    width: min(100%, var(--column));
    margin-inline: auto;
  }

  .nav {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: calc(14px + var(--safe-top)) 20px 12px;
  }

  .chev {
    flex: none;
    width: 44px;
    height: 44px;
    margin-left: -10px;
    display: grid;
    place-items: center;
    background: none;
    border: 0;
    color: var(--paper-dim);
  }

  .label-back {
    font-size: 0.8rem;
    color: var(--paper-dim);
  }

  .head {
    padding: 0 20px 16px;
    background: radial-gradient(90% 120% at 50% -10%, rgba(201, 162, 39, 0.2), rgba(15, 13, 11, 0) 70%);
  }

  .identity {
    display: flex;
    gap: 14px;
    align-items: flex-start;
    margin-bottom: 14px;
  }

  .avatar {
    flex: none;
    width: 52px;
    height: 52px;
    border-radius: 999px;
    background: var(--rule);
    display: grid;
    place-items: center;
    font-family: var(--serif);
    font-size: 1.4rem;
    color: var(--brass);
  }

  .names {
    flex: 1;
    min-width: 0;
  }

  h2 {
    font-size: 1.5rem;
    line-height: 1.16;
    margin: 0 0 2px;
    color: var(--paper-bright);
  }

  .handle {
    margin: 0;
    font-size: 0.85rem;
    color: var(--paper-dim);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .counts {
    margin: 4px 0 0;
    font-size: 0.82rem;
    color: var(--paper-dim);
  }

  /* The copyable address: the reason this page has its own route. */
  .address {
    display: flex;
    align-items: center;
    background: var(--panel);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    overflow: hidden;
  }

  .url {
    flex: 1;
    min-width: 0;
    padding: 0 12px;
    line-height: 44px;
    font-family: var(--mono);
    font-size: 0.78rem;
    color: var(--paper-dim);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .copy {
    flex: none;
    width: 44px;
    height: 44px;
    display: grid;
    place-items: center;
    background: none;
    border: 0;
    border-left: 1px solid var(--rule);
    color: var(--brass);
  }

  .public {
    margin: 8px 0 0;
    font-size: 0.8rem;
    color: var(--paper-dim);
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 14px 20px 6px;
  }

  .chip {
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    padding: 0 14px;
    background: none;
    border: 1px solid var(--rule);
    border-radius: 999px;
    color: var(--paper-dim);
    font-size: 0.82rem;
  }

  .chip.on {
    background: var(--brass);
    border-color: var(--brass);
    color: var(--ink);
    font-weight: 600;
  }

  .notice {
    padding: 2rem 22px 3rem;
    color: var(--paper-dim);
  }

  @media (min-width: 44rem) {
    .rail {
      width: min(100% - 2.5rem, var(--column));
      margin-inline: auto;
      box-shadow: 0 10px 24px rgba(0, 0, 0, 0.55);
    }
  }
</style>
