<script>
  /**
   * 1. Review — the hero.
   *
   * Cover left at real size, review title as a large serif headline, rating as
   * brass marks, body in serif at reading width. When the post is sensitive the
   * body blurs with the warning legible above it.
   */
  import Cover from '../Cover.svelte';
  import Rating from '../Rating.svelte';
  import RichText from '../RichText.svelte';
  import BookLine from '../BookLine.svelte';
  import Byline from '../Byline.svelte';
  import Spoiler from '../Spoiler.svelte';
  import Actions from '../Actions.svelte';
  import { plain } from '../../lib/sanitise.js';

  let { item, account = null, onperson = null, onbook = null, onreply = null } = $props();

  const warning = $derived(plain(item.core.spoiler_text));
  const sensitive = $derived(Boolean(item.enrichment.sensitiv || item.core.sensitive));
</script>

<article class="review enters">
  <Byline account={item.core.account} createdAt={item.core.created_at} url={item.core.url} {onperson} />

  <div class="layout">
    <Cover book={item.book} size="large" />

    <div class="text">
      {#if item.enrichment.tittel}
        <h2>{item.enrichment.tittel}</h2>
      {/if}
      <Rating value={item.enrichment.vurdering} />

      {#if sensitive}
        <Spoiler warning={warning || item.enrichment.aatvaring || ''}>
          <RichText html={item.enrichment.innhald || item.core.content} />
        </Spoiler>
      {:else}
        <RichText html={item.enrichment.innhald || item.core.content} />
      {/if}
    </div>
  </div>

  <BookLine book={item.book} {onbook} />
  <Actions {item} {account} {onreply} />
</article>

<style>
  .review {
    background: var(--ink-800);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 1.25rem 1.35rem;
    display: grid;
    gap: 1rem;
  }

  .layout {
    display: flex;
    gap: 1.35rem;
    align-items: flex-start;
  }

  .text {
    min-width: 0;
    display: grid;
    gap: 0.7rem;
    align-content: start;
  }

  h2 {
    font-size: var(--step-3);
    margin: 0;
    color: var(--paper);
  }

  @media (max-width: 34rem) {
    .layout {
      flex-direction: column;
      gap: 1rem;
    }
  }
</style>
