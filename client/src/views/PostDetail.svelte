<script>
  /**
   * One post, on the desk under the lamp (4f).
   *
   * The only screen where the cover is centred and large: 180px, on its own,
   * because here you are looking at the book rather than scanning past it.
   * The prose is never clamped here — this is where "Les heile omtalen" leads,
   * so clamping it again would be a loop.
   *
   * The rating shows its numeric equivalent visibly as well as to a screen
   * reader, and the author row's "Hylla" button goes to that person's own page
   * rather than setting a filter on the feed.
   *
   * Back returns to the feed with the same filters and the same scroll position
   * (lib/router.svelte.js).
   */
  import Icon from '../components/Icon.svelte';
  import Cover from '../components/Cover.svelte';
  import Rating from '../components/Rating.svelte';
  import RichText from '../components/RichText.svelte';
  import Progress from '../components/Progress.svelte';
  import Spoiler from '../components/Spoiler.svelte';
  import Actions from '../components/Actions.svelte';
  import { feed } from '../lib/collection.svelte.js';
  import { decodeId } from '../lib/ids.js';
  import * as server from '../lib/server.js';
  import { handleOf } from '../lib/filters.js';
  import { plain, countParagraphs } from '../lib/sanitise.js';
  import { t, tParts, formatAge, formatMonth, formatNumber } from '../lib/i18n.svelte.js';
  import { back } from '../lib/router.svelte.js';

  let { id, account = null, onperson, onbook, onreply } = $props();

  const uri = $derived(decodeId(id));

  /** From the collection first; only a direct link ever needs the network. */
  let fetched = $state(null);
  /** null | 'gone' | 'unreachable' — two different things, said differently. */
  let problem = $state(null);

  const item = $derived(feed.items.find((held) => held.core.uri === uri) || fetched);

  $effect(() => {
    if (!uri || item) return;
    let cancelled = false;
    (async () => {
      try {
        const { entries, books } = await server.enrich([uri]);
        const entry = entries[uri];
        if (cancelled) return;
        if (!entry) {
          // The server answered and had nothing: the post really is gone.
          problem = 'gone';
          return;
        }
        fetched = {
          id: uri,
          core: {
            uri,
            url: uri,
            created_at: entry.publisert || null,
            account: null,
            sensitive: Boolean(entry.sensitiv),
            spoiler_text: entry.aatvaring || '',
            id: null,
            favourited: false,
            reblogged: false,
          },
          boostedBy: null,
          enrichment: entry,
          book: entry.bok ? books[entry.bok] || null : null,
          resolved: false,
        };
      } catch {
        // No answer at all — a timeout, a rate limit, no network. That is not
        // the same as "this post no longer exists", and saying the wrong one
        // sends the reader looking for a post that is fine.
        if (!cancelled) problem = 'unreachable';
      }
    })();
    return () => {
      cancelled = true;
    };
  });

  const who = $derived(
    plain(item?.core.account?.display_name) ||
      item?.core.account?.username ||
      item?.core.account?.acct ||
      '',
  );
  const body = $derived(item?.enrichment.innhald || item?.core.content || '');
  const passage = $derived(item?.enrichment.sitat || '');
  const warning = $derived(plain(item?.core.spoiler_text) || item?.enrichment.aatvaring || '');
  const sensitive = $derived(Boolean(item?.enrichment.sensitiv || item?.core.sensitive));
  const quotation = $derived(item?.enrichment.slag === 'sitat');
  const status = $derived(item?.enrichment.slag === 'lesestatus');
  const inferred = $derived(item?.enrichment.status === 'utrekna');

  const SENTENCES = {
    'vil-lesa': 'status.wantToRead',
    byrja: 'status.started',
    ferdig: 'status.finished',
    utrekna: 'status.stale',
  };

  const sentence = $derived(
    !status
      ? []
      : tParts(SENTENCES[item.enrichment.status] || 'status.updated', {
          who,
          title: item.book?.tittel || t('cover.unknown'),
          since: formatMonth(item.core.created_at),
        }),
  );
</script>

<div class="detail fades">
  <header>
    <button type="button" class="chev" aria-label={t('nav.back')} onclick={() => back()}>
      <Icon name="back" size={20} />
    </button>
    <span class="where">
      {#if item}{t(`kind.${item.enrichment.slag}`)}{#if who} · {who}{/if}{:else}{t('feed.loading')}{/if}
    </span>
  </header>

  {#if problem}
    <div class="gone">
      <h2>{t(problem === 'gone' ? 'error.gone' : 'error.unreachable')}</h2>
      <p>{t(problem === 'gone' ? 'error.goneDetail' : 'error.unreachableDetail')}</p>
      {#if problem === 'unreachable'}
        <button type="button" class="secondary" onclick={() => (problem = null)}>
          {t('feed.retry')}
        </button>
      {/if}
    </div>
  {:else if !item}
    <p class="waiting">{t('feed.loading')}</p>
  {:else}
    <div class="lit">
      <div class="centre">
        <Cover book={item.book} width={180} {onbook} />
      </div>

      {#if item.enrichment.tittel}<h2>{item.enrichment.tittel}</h2>{/if}

      {#if item.enrichment.vurdering !== null && item.enrichment.vurdering !== undefined}
        <div class="rated">
          <Rating value={item.enrichment.vurdering} size={0.75} />
          <!-- The figure is shown, not only announced. -->
          <span class="figure">
            {t('card.ratingOf', { rating: formatNumber(item.enrichment.vurdering) })}
          </span>
        </div>
      {/if}

      {#if status}
        <p class="sentence">
          {#each sentence as part, index (index)}
            {#if part.slot === 'title'}<span class="title">{part.value}</span>
            {:else if part.slot}{part.value}
            {:else}{part.text}{/if}
          {/each}
        </p>
        {#if inferred}
          <span class="badge">
            <Icon name="bang" size={12} stroke={1.3} />
            {t('status.inferredBy')}
          </span>
        {/if}
      {:else if sensitive}
        <Spoiler {warning} paragraphs={countParagraphs(passage || body)}>
          {#if quotation}
            <blockquote><RichText html={passage || body} tone="quote" /></blockquote>
          {:else}
            <RichText html={body} tone="detail" />
          {/if}
        </Spoiler>
      {:else if quotation}
        <blockquote><RichText html={passage || body} tone="quote" /></blockquote>
      {:else}
        <RichText html={body} tone="detail" />
      {/if}

      <Progress enrichment={item.enrichment} pages={item.book?.sider ?? null} />

      {#if item.book}
        <button type="button" class="book-row" onclick={() => onbook?.(item.book)}>
          <span class="thumb"><Cover book={item.book} width={26} /></span>
          <span class="names">
            <span class="book-title">{item.book.tittel || t('cover.unknown')}</span>
            {#if (item.book.forfattarar || []).length}
              <span class="book-author">{item.book.forfattarar.join(', ')}</span>
            {/if}
          </span>
          <Icon name="forward" size={18} />
        </button>
      {/if}

      {#if item.core.account}
        <div class="person">
          <span class="avatar" aria-hidden="true">{(who || '?').slice(0, 1)}</span>
          <span class="whom">
            <span class="name">{who}</span>
            <span class="handle">
              {handleOf(item.core.account)} · {formatAge(item.core.created_at)}
            </span>
          </span>
          <button type="button" class="shelf-of" onclick={() => onperson?.(item.core.account)}>
            {t('person.shelf')}
          </button>
        </div>
      {/if}
    </div>

    {#if !item.inferred}
      <div class="bar">
        <div class="bar-inner">
          <Actions {item} {account} {onreply} big />
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .detail {
    padding-bottom: calc(var(--tabbar) + 46px + var(--safe-bottom));
  }

  header {
    position: sticky;
    top: 0;
    z-index: 5;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: calc(14px + var(--safe-top)) 20px 14px;
    border-bottom: 1px solid var(--rule);
    background: var(--ink);
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

  .where {
    font-size: 0.8rem;
    color: var(--paper-dim);
  }

  .lit {
    width: min(100%, var(--column));
    margin-inline: auto;
    padding: 22px 22px 0;
    background: radial-gradient(100% 60% at 50% 0, rgba(201, 162, 39, 0.16), rgba(15, 13, 11, 0) 62%);
  }

  .centre {
    display: flex;
    justify-content: center;
    margin-bottom: 18px;
  }

  h2 {
    font-size: 1.7rem;
    line-height: 1.16;
    margin: 0 0 10px;
    color: var(--paper-bright);
  }

  .rated {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }

  .figure {
    font-size: 0.8rem;
    color: var(--paper-dim);
  }

  blockquote {
    margin: 0 0 8px;
  }

  .sentence {
    margin: 0;
    font-size: 1rem;
    color: var(--paper-dim);
  }

  .title {
    font-family: var(--serif);
    color: var(--paper-bright);
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 10px;
    padding: 3px 8px;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--paper-dim);
    border: 1px dashed var(--grey-dashed);
    border-radius: var(--radius-cover);
  }

  .book-row {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    min-height: 56px;
    margin-top: 18px;
    padding: 8px 12px;
    background: var(--panel);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    text-align: left;
    color: var(--paper-dim);
  }

  .thumb {
    flex: none;
    display: flex;
  }

  .names {
    flex: 1;
    min-width: 0;
    display: grid;
  }

  .book-title {
    font-family: var(--serif);
    font-size: 0.98rem;
    color: var(--paper);
  }

  .book-author {
    font-size: 0.8rem;
    color: var(--paper-dim);
  }

  .person {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 18px;
    padding-top: 14px;
    border-top: 1px solid var(--rule);
  }

  .avatar {
    flex: none;
    width: 32px;
    height: 32px;
    border-radius: 999px;
    background: var(--rule);
    display: grid;
    place-items: center;
    font-family: var(--serif);
    font-size: 0.9rem;
    color: var(--brass);
  }

  .whom {
    min-width: 0;
    display: grid;
  }

  .name {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--paper);
  }

  .handle {
    font-size: 0.78rem;
    color: var(--paper-dim);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .shelf-of {
    flex: none;
    margin-left: auto;
    min-height: 44px;
    padding: 0 14px;
    background: none;
    border: 1px solid var(--rule);
    border-radius: 999px;
    color: var(--brass);
    font-size: 0.82rem;
  }

  /* The action bar is fixed above the tab bar: it is the point of the screen. */
  .bar {
    position: fixed;
    left: 0;
    right: 0;
    bottom: calc(var(--tabbar) + var(--safe-bottom));
    z-index: 12;
    padding: 10px 16px 16px;
    border-top: 1px solid var(--rule);
    background: var(--ink-deep);
  }

  .bar-inner {
    width: min(100%, var(--column));
    margin-inline: auto;
  }

  .gone,
  .waiting {
    width: min(100% - 44px, var(--column));
    margin: 3rem auto;
    color: var(--paper-dim);
  }

  .gone h2 {
    font-size: 1.45rem;
    color: var(--paper-bright);
  }

  @media (min-width: 44rem) {
    .bar {
      bottom: 0;
    }
  }
</style>
