<script>
  /**
   * Picks the card for the post kind, and wraps it in the boost frame when the
   * post arrived as somebody else's boost.
   *
   * Any card can sit inside a hairline frame with a small ribbon. The inner
   * card keeps its own design — a boosted quotation is still a quotation.
   */
  import ReviewCard from './cards/ReviewCard.svelte';
  import RatingCard from './cards/RatingCard.svelte';
  import CommentCard from './cards/CommentCard.svelte';
  import QuotationCard from './cards/QuotationCard.svelte';
  import ReadingStatusCard from './cards/ReadingStatusCard.svelte';
  import { plain } from '../lib/sanitise.js';
  import { t } from '../lib/i18n.svelte.js';

  let { item, account = null, onperson = null, onbook = null, onreply = null } = $props();

  const CARDS = {
    omtale: ReviewCard,
    vurdering: RatingCard,
    kommentar: CommentCard,
    sitat: QuotationCard,
    lesestatus: ReadingStatusCard,
  };

  const Chosen = $derived(CARDS[item.enrichment.slag] || CommentCard);
  const booster = $derived(
    item.boostedBy
      ? plain(item.boostedBy.display_name) || item.boostedBy.username || item.boostedBy.acct
      : null,
  );
</script>

{#if booster}
  <div class="boost">
    <p class="ribbon">{t('card.boostedBy', { name: booster })}</p>
    <div class="inner">
      <Chosen {item} {account} {onperson} {onbook} {onreply} />
    </div>
  </div>
{:else}
  <Chosen {item} {account} {onperson} {onbook} {onreply} />
{/if}

<style>
  .boost {
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 0.35rem;
  }

  .ribbon {
    margin: 0 0 0.35rem;
    padding: 0.15em 0.6em;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--paper-dim);
  }

  /* A full-bleed quotation inside a boost frame must stay inside the frame. */
  .inner {
    --bleed: 0.75rem;
    overflow: hidden;
    border-radius: var(--radius);
  }
</style>
