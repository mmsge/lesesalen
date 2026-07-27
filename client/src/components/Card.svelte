<script>
  /**
   * One post model, five cards. Adding a kind means adding one line to `CARDS`
   * and one component — nothing else in the feed needs to know.
   *
   * The boost frame the old design had is gone: an outbox is an account's own
   * output, so nothing collected here arrived as somebody else's boost
   * (ADR 0008). Where a boost can still be known, the card says so in its kind
   * label rather than wrapping itself in a second frame.
   */
  import ReviewCard from './cards/ReviewCard.svelte';
  import RatingCard from './cards/RatingCard.svelte';
  import CommentCard from './cards/CommentCard.svelte';
  import QuotationCard from './cards/QuotationCard.svelte';
  import ReadingStatusCard from './cards/ReadingStatusCard.svelte';

  let {
    item,
    account = null,
    onopen = null,
    onperson = null,
    onbook = null,
    onreply = null,
  } = $props();

  const CARDS = {
    omtale: ReviewCard,
    vurdering: RatingCard,
    kommentar: CommentCard,
    sitat: QuotationCard,
    lesestatus: ReadingStatusCard,
  };

  const Chosen = $derived(CARDS[item.enrichment.slag] || CommentCard);
</script>

<Chosen {item} {account} {onopen} {onperson} {onbook} {onreply} />
