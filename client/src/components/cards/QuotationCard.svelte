<script>
  /**
   * 3. Quotation — the lamp cone.
   *
   * Full-bleed, no frame: just light falling off towards the edges, an oversized
   * quotation mark bleeding off the top left, and the passage set large. Then a
   * brass tick and "Is-slottet, s. 41" in small caps.
   *
   * This is the visual punctuation of the feed — it is supposed to interrupt —
   * and it is the one card that is **never clamped**. A truncated quotation is
   * not a quotation.
   */
  import RichText from '../RichText.svelte';
  import Byline from '../Byline.svelte';
  import Spoiler from '../Spoiler.svelte';
  import Actions from '../Actions.svelte';
  import { plain, countParagraphs } from '../../lib/sanitise.js';
  import { hasProgress } from '../../lib/progress.js';
  import { t, formatNumber } from '../../lib/i18n.svelte.js';
  import { openable } from '../../lib/openable.js';

  let {
    item,
    account = null,
    onopen = null,
    onperson = null,
    onbook = null,
    onreply = null,
  } = $props();

  const passage = $derived(item.enrichment.sitat || item.enrichment.innhald || item.core.content || '');
  const warning = $derived(plain(item.core.spoiler_text) || item.enrichment.aatvaring || '');
  const sensitive = $derived(Boolean(item.enrichment.sensitiv || item.core.sensitive));
  const title = $derived(item.book?.tittel || t('cover.unknown'));

  /**
   * "Is-slottet, s. 41" — and just "Is-slottet" when there is no page position,
   * which is the common case. The page half only ever comes from a real `PG`
   * position (§Data contract).
   */
  const source = $derived(
    hasProgress(item.enrichment)
      ? t('card.sourceWithPage', {
          title,
          page: formatNumber(item.enrichment.posisjon),
        })
      : title,
  );

  /** Where a tap on the card goes, for anyone who cannot see that it is a card. */
  const openLabel = $derived(
    t('card.open', {
      kind: t('kind.sitat'),
      who:
        plain(item.core.account?.display_name) ||
        item.core.account?.username ||
        item.core.account?.acct ||
        '',
    }),
  );
</script>

<article class="quotation enters" use:openable={{ onopen: () => onopen?.(item), label: openLabel }}>
  <span class="glyph" aria-hidden="true">&ldquo;</span>

  {#if sensitive}
    <Spoiler {warning} paragraphs={countParagraphs(passage)}>
      <blockquote><RichText html={passage} tone="quote" /></blockquote>
    </Spoiler>
  {:else}
    <blockquote><RichText html={passage} tone="quote" /></blockquote>
  {/if}

  <div class="foot">
    <span class="tick" aria-hidden="true"></span>
    {#if item.book && onbook}
      <button
        type="button"
        class="source"
        onclick={(event) => {
          event.stopPropagation();
          onbook(item.book);
        }}
      >
        {source}
      </button>
    {:else}
      <span class="source">{source}</span>
    {/if}
    <div class="spacer"></div>
    <Byline account={item.core.account} createdAt={item.core.created_at} {onperson} />
  </div>

  <div class="row">
    <Actions {item} {account} {onreply} />
  </div>
</article>

<style>
  .quotation {
    position: relative;
    padding: 40px 22px 20px;
    overflow: hidden;
    cursor: pointer;
    background: radial-gradient(
      85% 75% at 50% 8%,
      rgba(201, 162, 39, 0.22),
      rgba(34, 29, 22, 0.96) 62%,
      var(--panel)
    );
  }

  .glyph {
    position: absolute;
    top: -40px;
    left: 6px;
    font-family: var(--serif);
    font-size: 10rem;
    line-height: 1;
    color: var(--brass);
    opacity: 0.16;
    pointer-events: none;
    user-select: none;
  }

  blockquote {
    position: relative;
    margin: 0 0 16px;
  }

  .foot {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.85rem;
    color: var(--paper-dim);
    flex-wrap: wrap;
  }

  .tick {
    flex: none;
    width: 22px;
    height: 1px;
    background: var(--brass);
  }

  .source {
    font-variant-caps: small-caps;
    letter-spacing: 0.05em;
    white-space: nowrap;
    background: none;
    border: 0;
    padding: 0;
    font: inherit;
    font-variant-caps: small-caps;
    color: var(--paper-dim);
  }

  button.source {
    min-height: 44px;
    color: var(--paper);
  }

  .spacer {
    flex: 1;
  }

  .row {
    display: flex;
    justify-content: flex-end;
  }
</style>
