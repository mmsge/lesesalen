<script>
  /**
   * 3. Comment — the marginal note.
   *
   * Slightly inset, warmer tint, a hairline down the left edge like a margin
   * rule. With a position, a thin progress bar: "side 143 av 400".
   */
  import Cover from '../Cover.svelte';
  import RichText from '../RichText.svelte';
  import Byline from '../Byline.svelte';
  import BookLine from '../BookLine.svelte';
  import Progress from '../Progress.svelte';
  import Spoiler from '../Spoiler.svelte';
  import Actions from '../Actions.svelte';
  import { plain } from '../../lib/sanitise.js';

  let { item, account = null, onperson = null, onbook = null, onreply = null } = $props();

  const warning = $derived(plain(item.core.spoiler_text));
  const sensitive = $derived(Boolean(item.enrichment.sensitiv || item.core.sensitive));
</script>

<article class="note enters">
  <div class="layout">
    <Cover book={item.book} size="small" />
    <div class="text">
      <Byline account={item.core.account} createdAt={item.core.created_at} url={item.core.url} {onperson} />

      {#if sensitive}
        <Spoiler warning={warning || item.enrichment.aatvaring || ''}>
          <RichText html={item.enrichment.innhald || item.core.content} tone="small" />
        </Spoiler>
      {:else}
        <RichText html={item.enrichment.innhald || item.core.content} tone="small" />
      {/if}

      <Progress
        position={item.enrichment.posisjon}
        mode={item.enrichment.posisjonsmodus}
        pages={item.book?.sider ?? null}
      />
      <BookLine book={item.book} {onbook} />
      <Actions {item} {account} {onreply} />
    </div>
  </div>
</article>

<style>
  .note {
    margin-left: 1.5rem;
    background: var(--ink-700);
    border: 1px solid var(--rule);
    border-left: 2px solid var(--brass);
    border-radius: var(--radius);
    padding: 0.9rem 1.1rem;
  }

  .layout {
    display: flex;
    gap: 0.9rem;
    align-items: flex-start;
  }

  .text {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 0.55rem;
  }

  @media (max-width: 34rem) {
    .note {
      margin-left: 0.5rem;
    }
  }
</style>
