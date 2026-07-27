<script>
  /**
   * The book, held up to the lamp (4g, corrected by 5i).
   *
   * Opened by a long press on any cover or spine, or a right-click on a desktop.
   * It is a history entry, so back closes it and the feed underneath is
   * untouched.
   *
   * **Missing Edition fields disappear.** `undertittel`, `aar`, `sider` and
   * `serie` come from a per-Edition fetch that may never have happened or may
   * simply not carry them. When one is missing it is omitted entirely — no
   * "ukjend", no em dash — so the meta line can collapse to a single item or
   * vanish, and the layout is built to let it. A series shows its **name only**:
   * the number is not captured anywhere, and inventing "I" would be a
   * bibliographic claim we cannot support.
   *
   * The last line is the honest one: Lesesalen cannot shelve anything. It reads
   * BookWyrm; it does not write to it.
   */
  import Sheet from './Sheet.svelte';
  import Cover from './Cover.svelte';
  import { t, formatNumber } from '../lib/i18n.svelte.js';
  import { show } from '../lib/toast.svelte.js';

  let { book, posts = 0, onclose, onfilter } = $props();

  /** Only the parts that exist. An empty list renders nothing at all. */
  const meta = $derived(
    [
      book?.serie || null,
      // A year is not a quantity: 1920, never "1 920".
      book?.aar ? String(book.aar) : null,
      book?.sider ? t('book.pages', { pages: formatNumber(book.sider) }) : null,
    ].filter(Boolean),
  );

  const author = $derived((book?.forfattarar || []).join(', '));
  const link = $derived(book?.bookwyrm_url || null);
  const host = $derived.by(() => {
    if (!link) return null;
    try {
      return new URL(link).hostname;
    } catch {
      return null;
    }
  });

  async function copy() {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      show('book.copied');
    } catch {
      show('book.copyFailed', 'warn');
    }
  }
</script>

<Sheet {onclose} label={book?.tittel || t('cover.unknown')}>
  <div class="head">
    <Cover {book} width={104} />
    <div class="facts">
      <h2>{book?.tittel || t('cover.unknown')}</h2>
      {#if book?.undertittel}<p class="subtitle">{book.undertittel}</p>{/if}
      {#if author}<p class="author">{author}</p>{/if}
      {#if meta.length}<p class="meta">{meta.join(' · ')}</p>{/if}
      <p class="count">{t('book.postsHere', { n: formatNumber(posts) })}</p>
    </div>
  </div>

  <div class="actions">
    <button type="button" class="primary" onclick={() => onfilter?.(book)}>
      {t('book.filterOn')}
    </button>
    {#if link}
      <a class="secondary" href={link} rel="nofollow noopener noreferrer" target="_blank">
        {host ? t('book.openOn', { host }) : t('book.open')}
      </a>
      <button type="button" class="secondary" onclick={copy}>{t('book.copy')}</button>
    {/if}
  </div>

  <p class="caveat">{t('book.cannotShelve')}</p>
</Sheet>

<style>
  .head {
    display: flex;
    gap: 16px;
    align-items: flex-start;
  }

  .facts {
    flex: 1;
    min-width: 0;
  }

  h2 {
    font-size: 1.35rem;
    line-height: 1.18;
    margin: 0 0 4px;
    color: var(--paper-bright);
  }

  .subtitle {
    margin: 0 0 4px;
    font-family: var(--serif);
    font-size: 0.98rem;
    color: var(--paper-prose);
  }

  .author {
    margin: 0 0 2px;
    font-size: 0.95rem;
    color: var(--paper);
  }

  .meta {
    margin: 0 0 10px;
    font-size: 0.82rem;
    color: var(--paper-dim);
  }

  .count {
    margin: 0;
    font-size: 0.85rem;
    color: var(--paper-dim);
  }

  .actions {
    display: grid;
    gap: 9px;
    margin: 18px 0 0;
  }

  .actions a {
    text-decoration: none;
  }

  .caveat {
    margin: 14px 0 0;
    font-size: 0.82rem;
    color: var(--paper-dim);
  }
</style>
