<script>
  /**
   * 4. Comment — the marginal note.
   *
   * No cover, and a 2px rule down the left edge like a margin mark. The rule is
   * **brass when the post carries a real page position and `--rule` when it
   * does not** — and the grey variant is the norm, because `positionMode: PG`
   * is rare (§Data contract). Never colour it from anything else.
   */
  import RichText from '../RichText.svelte';
  import Byline from '../Byline.svelte';
  import Progress from '../Progress.svelte';
  import Spoiler from '../Spoiler.svelte';
  import Actions from '../Actions.svelte';
  import { plain, countParagraphs } from '../../lib/sanitise.js';
  import { hasProgress } from '../../lib/progress.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { openable } from '../../lib/openable.js';

  let {
    item,
    account = null,
    onopen = null,
    onperson = null,
    onreply = null,
  } = $props();

  const body = $derived(item.enrichment.innhald || item.core.content || '');
  const warning = $derived(plain(item.core.spoiler_text) || item.enrichment.aatvaring || '');
  const sensitive = $derived(Boolean(item.enrichment.sensitiv || item.core.sensitive));
  const boosted = $derived(item.boostedBy ? plain(item.boostedBy.display_name) || item.boostedBy.acct : null);
  const progressed = $derived(hasProgress(item.enrichment));

  /** Where a tap on the card goes, for anyone who cannot see that it is a card. */
  const openLabel = $derived(
    t('card.open', {
      kind: t('kind.kommentar'),
      who:
        plain(item.core.account?.display_name) ||
        item.core.account?.username ||
        item.core.account?.acct ||
        '',
    }),
  );
</script>

<article class="note enters" use:openable={{ onopen: () => onopen?.(item), label: openLabel }}>
  <div class="margin" class:progressed>
    <p class="label dim">
      {t('kind.kommentar')}{#if boosted} · {t('card.boostedBy', { name: boosted })}{/if}
    </p>

    {#if sensitive}
      <Spoiler {warning} paragraphs={countParagraphs(body)}>
        <RichText html={body} />
      </Spoiler>
    {:else}
      <RichText html={body} />
    {/if}

    <Progress enrichment={item.enrichment} pages={item.book?.sider ?? null} />

    <div class="foot">
      <Byline account={item.core.account} createdAt={item.core.created_at} {onperson} />
      <div class="spacer"></div>
      <Actions {item} {account} {onreply} />
    </div>
  </div>
</article>

<style>
  .note {
    padding: 18px 20px 0;
    cursor: pointer;
  }

  .margin {
    border-left: 2px solid var(--rule);
    padding-left: 14px;
  }

  /* Brass only when there is a page position to point at. */
  .margin.progressed {
    border-left-color: var(--brass);
  }

  .label {
    margin-bottom: 6px;
  }

  .foot {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
  }

  .spacer {
    flex: 1;
  }
</style>
