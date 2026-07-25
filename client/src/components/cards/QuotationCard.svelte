<script>
  /**
   * 4. Quotation — breaks the grid.
   *
   * No card. Full bleed across the column, a shade different in background, the
   * passage in large serif, an outsize quotation glyph bled off the top left at
   * low opacity. Attribution and page below in small caps.
   *
   * This is the visual punctuation of the feed: it is supposed to interrupt.
   */
  import RichText from '../RichText.svelte';
  import Byline from '../Byline.svelte';
  import Progress from '../Progress.svelte';
  import Spoiler from '../Spoiler.svelte';
  import Actions from '../Actions.svelte';
  import { plain } from '../../lib/sanitise.js';
  import { t } from '../../lib/i18n.svelte.js';

  let { item, account = null, onperson = null, onbook = null, onreply = null } = $props();

  const warning = $derived(plain(item.core.spoiler_text));
  const sensitive = $derived(Boolean(item.enrichment.sensitiv || item.core.sensitive));
  const authors = $derived((item.book?.forfattarar || []).join(', '));
</script>

<article class="quotation enters">
  <figure>
    <span class="glyph" aria-hidden="true">&ldquo;</span>

    <blockquote>
      {#if sensitive}
        <Spoiler warning={warning || item.enrichment.aatvaring || ''}>
          <RichText html={item.enrichment.sitat || item.enrichment.innhald || item.core.content} tone="quote" />
        </Spoiler>
      {:else}
        <RichText html={item.enrichment.sitat || item.enrichment.innhald || item.core.content} tone="quote" />
      {/if}
    </blockquote>

    <figcaption>
      <span class="source">
        {#if item.book?.id && onbook}
          <button type="button" onclick={() => onbook(item.book.id)}>
            {item.book?.tittel || t('card.unknownBook')}
          </button>
        {:else}
          {item.book?.tittel || t('card.unknownBook')}
        {/if}
        {#if authors}<span class="authors">{t('card.byAuthor', { authors })}</span>{/if}
      </span>
      <Progress
        position={item.enrichment.posisjon}
        mode={item.enrichment.posisjonsmodus}
        pages={item.book?.sider ?? null}
      />
    </figcaption>
  </figure>

  <div class="foot">
    <Byline account={item.core.account} createdAt={item.core.created_at} url={item.core.url} {onperson} />
    <Actions {item} {account} {onreply} />
  </div>
</article>

<style>
  .quotation {
    position: relative;
    margin: 0;
    /* Full bleed: the quotation escapes the column the other cards sit in. */
    margin-inline: calc(var(--bleed, 1.5rem) * -1);
    padding: 2.5rem var(--bleed, 1.5rem) 1.5rem;
    background: var(--ink-700);
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
    overflow: hidden;
  }

  figure {
    margin: 0;
  }

  .glyph {
    position: absolute;
    top: -2.5rem;
    left: 0.2rem;
    font-family: var(--serif);
    font-size: 11rem;
    line-height: 1;
    color: var(--brass);
    opacity: 0.12;
    pointer-events: none;
    user-select: none;
  }

  blockquote {
    position: relative;
    margin: 0;
    font-family: var(--serif);
  }

  figcaption {
    margin-top: 1.1rem;
    display: grid;
    gap: 0.3rem;
  }

  .source {
    font-variant-caps: small-caps;
    letter-spacing: 0.04em;
    font-size: 0.95rem;
    color: var(--paper-dim);
  }

  .source button {
    background: none;
    border: 0;
    padding: 0;
    font: inherit;
    font-variant-caps: small-caps;
    color: var(--paper);
  }

  .source button:hover {
    color: var(--brass);
  }

  .authors {
    margin-left: 0.5em;
  }

  .foot {
    margin-top: 1rem;
    padding-top: 0.5rem;
    border-top: 1px solid var(--rule);
  }
</style>
