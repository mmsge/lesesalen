<script>
  /**
   * 2. Rating — the library slip.
   *
   * A 46px cover, bottom-aligned, then kind label, book title, rating and
   * byline in a tight stack. No prose, because there is none: a rating is the
   * whole post. Deliberately the smallest thing in the feed, so a run of them
   * reads as rhythm rather than as five identical cards.
   *
   * No action row either — frames 2a and 4l both draw this card without one,
   * and at 393px an action row leaves the byline about 77px, which truncates
   * "Åsta · 9 t sidan" to "Å · 9 t". Favourite, boost and reply are one tap
   * away on the post detail, which is where a card this small should send you.
   */
  import Cover from '../Cover.svelte';
  import Rating from '../Rating.svelte';
  import Byline from '../Byline.svelte';
  import { plain } from '../../lib/sanitise.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { openable } from '../../lib/openable.js';

  let { item, onopen = null, onperson = null, onbook = null } = $props();

  const boosted = $derived(item.boostedBy ? plain(item.boostedBy.display_name) || item.boostedBy.acct : null);

  /** Where a tap on the card goes, for anyone who cannot see that it is a card. */
  const openLabel = $derived(
    t('card.open', {
      kind: t('kind.vurdering'),
      who:
        plain(item.core.account?.display_name) ||
        item.core.account?.username ||
        item.core.account?.acct ||
        '',
    }),
  );
</script>

<article class="slip enters" use:openable={{ onopen: () => onopen?.(item), label: openLabel }}>
  <Cover book={item.book} width={46} {onbook} />

  <div class="body">
    <p class="label">
      {t('kind.vurdering')}{#if boosted} · {t('card.boostedBy', { name: boosted })}{/if}
    </p>
    <span class="title">{item.book?.tittel || t('cover.unknown')}</span>
    <div class="line">
      <Rating value={item.enrichment.vurdering} size={0.6} />
      <Byline account={item.core.account} createdAt={item.core.created_at} {onperson} />
    </div>
  </div>
</article>

<style>
  .slip {
    display: flex;
    gap: 14px;
    align-items: flex-end;
    padding: 16px 20px 0;
    cursor: pointer;
    background: radial-gradient(90% 90% at 12% 100%, rgba(201, 162, 39, 0.1), rgba(15, 13, 11, 0) 60%);
  }

  .body {
    flex: 1;
    min-width: 0;
    padding-bottom: 8px;
  }

  .label {
    margin-bottom: 3px;
  }

  .title {
    display: block;
    font-family: var(--serif);
    font-size: 1.2rem;
    color: var(--paper-bright);
  }

  /* One line, deliberately: the rating card is the smallest thing in the feed,
     and it stops being that the moment the actions wrap onto a second row. The
     byline gives up its width first. */
  .line {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 5px;
    min-width: 0;
    flex-wrap: wrap;
  }

  .line :global(.byline) {
    min-width: 0;
    overflow: hidden;
  }

  .line :global(.byline .who) {
    max-width: 11rem;
  }
</style>
