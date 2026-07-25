<script>
  /** Title, authors and page count — the bibliographic line under every card. */
  import { t } from '../lib/i18n.svelte.js';

  let { book = null, onbook = null } = $props();

  const authors = $derived((book?.forfattarar || []).join(', '));
</script>

<div class="book">
  <span class="title">{book?.tittel || t('card.unknownBook')}</span>
  {#if authors}
    <span class="authors">{t('card.byAuthor', { authors })}</span>
  {/if}
  <span class="links">
    {#if book?.id && onbook}
      <button type="button" class="chip" onclick={() => onbook(book.id)}>
        {t('action.byBook')}
      </button>
    {/if}
    {#if book?.bookwyrm_url}
      <a href={book.bookwyrm_url} rel="nofollow noopener noreferrer" target="_blank">
        {t('card.openBook')}
      </a>
    {/if}
  </span>
</div>

<style>
  .book {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.4em 0.6em;
    font-size: 0.92rem;
    color: var(--paper-dim);
  }

  .title {
    font-family: var(--serif);
    color: var(--paper);
  }

  .links {
    display: inline-flex;
    gap: 0.75em;
    margin-left: auto;
    font-size: 0.85rem;
  }

  .chip {
    background: none;
    border: 0;
    padding: 0;
    color: var(--brass);
    text-decoration: underline;
    text-underline-offset: 0.15em;
  }

  .chip:hover {
    color: var(--paper);
  }
</style>
