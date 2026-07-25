<script>
  /**
   * 2. Rating only — the library slip.
   *
   * Short, wide, quiet. Cover thumbnail, title, rating marks, nothing else.
   * Deliberately the smallest thing in the feed, so a run of them reads as
   * rhythm rather than as five identical posts.
   */
  import Cover from '../Cover.svelte';
  import Rating from '../Rating.svelte';
  import Byline from '../Byline.svelte';
  import Actions from '../Actions.svelte';
  import { t } from '../../lib/i18n.svelte.js';

  let { item, account = null, onperson = null, onbook = null, onreply = null } = $props();

  const authors = $derived((item.book?.forfattarar || []).join(', '));
</script>

<article class="slip enters">
  <Cover book={item.book} size="small" />

  <div class="body">
    <div class="line">
      {#if item.book?.id && onbook}
        <button type="button" class="title" onclick={() => onbook(item.book.id)}>
          {item.book?.tittel || t('card.unknownBook')}
        </button>
      {:else}
        <span class="title">{item.book?.tittel || t('card.unknownBook')}</span>
      {/if}
      {#if authors}<span class="authors">{t('card.byAuthor', { authors })}</span>{/if}
      <Rating value={item.enrichment.vurdering} size="small" />
    </div>
    <Byline account={item.core.account} createdAt={item.core.created_at} url={item.core.url} {onperson} />
    <Actions {item} {account} {onreply} />
  </div>
</article>

<style>
  .slip {
    display: flex;
    gap: 0.9rem;
    align-items: flex-start;
    background: var(--ink-800);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 0.75rem 0.9rem;
  }

  .body {
    flex: 1;
    min-width: 0;
  }

  .line {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.4em 0.7em;
    margin-bottom: 0.3em;
  }

  .title {
    font-family: var(--serif);
    font-size: var(--step-1);
    color: var(--paper);
    background: none;
    border: 0;
    padding: 0;
    text-align: left;
  }

  button.title:hover {
    color: var(--brass);
  }

  .authors {
    font-size: 0.88rem;
    color: var(--paper-dim);
  }
</style>
