<script>
  /**
   * 1. Review — the hero.
   *
   * A 132px cover, tilted a degree and a half, bottom-aligned with the title
   * block beside it, under its own lamp wash. Kind label above, title in
   * Literata, then the rating, then prose, then byline and actions.
   *
   * Long reviews clamp to 152px with a fade and a button into the detail (4j);
   * they are never expanded in place, because a feed of half-expanded reviews
   * loses the rhythm the five card kinds exist to create.
   */
  import Cover from '../Cover.svelte';
  import Rating from '../Rating.svelte';
  import RichText from '../RichText.svelte';
  import Byline from '../Byline.svelte';
  import Spoiler from '../Spoiler.svelte';
  import Actions from '../Actions.svelte';
  import { plain, countParagraphs } from '../../lib/sanitise.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { openable } from '../../lib/openable.js';

  let {
    item,
    account = null,
    onopen = null,
    onperson = null,
    onbook = null,
    onreply = null,
  } = $props();

  const CLAMP_AT = 220;

  const body = $derived(item.enrichment.innhald || item.core.content || '');
  const warning = $derived(plain(item.core.spoiler_text) || item.enrichment.aatvaring || '');
  const sensitive = $derived(Boolean(item.enrichment.sensitiv || item.core.sensitive));
  const long = $derived(plain(body).length > CLAMP_AT);
  const boosted = $derived(item.boostedBy ? plain(item.boostedBy.display_name) || item.boostedBy.acct : null);

  /** Where a tap on the card goes, for anyone who cannot see that it is a card. */
  const openLabel = $derived(
    t('card.open', {
      kind: t('kind.omtale'),
      who:
        plain(item.core.account?.display_name) ||
        item.core.account?.username ||
        item.core.account?.acct ||
        '',
    }),
  );
</script>

<article class="review enters" use:openable={{ onopen: () => onopen?.(item), label: openLabel }}>
  <p class="label">
    {t('kind.omtale')}{#if boosted} · {t('card.boostedBy', { name: boosted })}{/if}
  </p>

  <div class="head">
    <Cover book={item.book} width={132} tilt {onbook} />
    <div class="titling">
      {#if item.enrichment.tittel}<h2>{item.enrichment.tittel}</h2>{/if}
      <Rating value={item.enrichment.vurdering} />
    </div>
  </div>

  <div class="body">
    {#if sensitive}
      <Spoiler {warning} paragraphs={countParagraphs(body)}>
        <RichText html={body} clamp={long} />
      </Spoiler>
    {:else}
      <RichText html={body} clamp={long} />
    {/if}
  </div>

  {#if long && !sensitive}
    <button
      type="button"
      class="read-all"
      onclick={(event) => {
        event.stopPropagation();
        onopen?.(item);
      }}
    >
      {t('post.readAll')}
    </button>
  {/if}

  <div class="foot">
    <Byline account={item.core.account} createdAt={item.core.created_at} {onperson} />
    <div class="spacer"></div>
    <Actions {item} {account} {onreply} />
  </div>
</article>

<style>
  .review {
    padding: 22px 20px 16px;
    cursor: pointer;
    /* Its own lamp cone, from the upper left. */
    background: radial-gradient(110% 80% at 22% 0, rgba(201, 162, 39, 0.13), rgba(15, 13, 11, 0) 62%);
  }

  .label {
    margin-bottom: 10px;
  }

  .head {
    display: flex;
    gap: 18px;
    align-items: flex-end;
  }

  .titling {
    flex: 1;
    min-width: 0;
    padding-bottom: 4px;
  }

  h2 {
    font-size: 1.45rem;
    line-height: 1.15;
    margin: 0 0 10px;
    color: var(--paper-bright);
  }

  .body {
    margin-top: 14px;
  }

  .read-all {
    width: 100%;
    min-height: 48px;
    margin-top: 4px;
    background: none;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    color: var(--brass);
    font-size: 0.92rem;
  }

  .foot {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
  }

  .spacer {
    flex: 1;
  }

  @media (min-width: 44rem) {
    /* Wide screen: the cover grows 132 → 168 (4m). */
    .head :global(.cover) {
      width: 168px !important;
    }
  }
</style>
