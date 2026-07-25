<script>
  /**
   * 5. Reading status — the stamp.
   *
   * A thin ticket strip, not a card. Four states, four treatments:
   *   vil lesa  dotted outline, dim
   *   byrja     brass arrow, solid rule
   *   ferdig    moss filled seal
   *   slutta    oxblood, struck through
   *
   * When BookWyrm's prose does not match any known phrasing the state is null
   * and the strip degrades to a plain "reading status" — see the note in
   * app/enrich.py about why that is the right failure.
   */
  import Cover from '../Cover.svelte';
  import Byline from '../Byline.svelte';
  import Actions from '../Actions.svelte';
  import { t } from '../../lib/i18n.svelte.js';

  let { item, account = null, onperson = null, onbook = null, onreply = null } = $props();

  const state = $derived(item.enrichment.status || 'ukjend');
  const authors = $derived((item.book?.forfattarar || []).join(', '));
</script>

<article class="ticket enters {state}">
  <span class="stamp">
    {#if state === 'byrja'}<span class="arrow" aria-hidden="true">→</span>{/if}
    {t(`status.${state}`)}
  </span>

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
    </div>
    <Byline account={item.core.account} createdAt={item.core.created_at} url={item.core.url} {onperson} />
    <Actions {item} {account} {onreply} />
  </div>
</article>

<style>
  .ticket {
    display: flex;
    align-items: flex-start;
    gap: 0.85rem;
    padding: 0.55rem 0.9rem;
    border-radius: var(--radius);
    background: transparent;
    border: 1px solid var(--rule);
  }

  .stamp {
    flex: none;
    align-self: center;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 0.2em 0.6em;
    border-radius: 2px;
    white-space: nowrap;
  }

  /* Vil lesa: dotted outline, dim. */
  .vil-lesa .stamp {
    border: 1px dotted var(--paper-dim);
    color: var(--paper-dim);
  }

  .vil-lesa {
    opacity: 0.8;
  }

  /* Byrja: brass arrow, solid rule. */
  .byrja .stamp {
    border: 1px solid var(--brass);
    color: var(--brass);
  }

  .byrja {
    border-left: 2px solid var(--brass);
  }

  .arrow {
    margin-right: 0.35em;
  }

  /* Ferdig: moss filled seal. */
  .ferdig .stamp {
    background: var(--moss);
    color: var(--paper);
    border: 1px solid var(--moss);
  }

  /* Slutta: oxblood, struck through. */
  .slutta .stamp {
    border: 1px solid var(--oxblood);
    color: var(--oxblood);
    text-decoration: line-through;
  }

  .slutta .title {
    text-decoration: line-through;
    text-decoration-color: var(--oxblood);
  }

  .ukjend .stamp {
    border: 1px solid var(--rule);
    color: var(--paper-dim);
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
  }

  .title {
    font-family: var(--serif);
    color: var(--paper);
    background: none;
    border: 0;
    padding: 0;
    font-size: var(--step-0);
    text-align: left;
  }

  button.title:hover {
    color: var(--brass);
  }

  .authors {
    font-size: 0.85rem;
    color: var(--paper-dim);
  }

  @media (max-width: 34rem) {
    .ticket {
      flex-wrap: wrap;
    }
  }
</style>
