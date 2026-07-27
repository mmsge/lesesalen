<script>
  /**
   * The ONLY place in this app that is allowed to use `{@html}`.
   *
   * Everything passed here goes through the DOMPurify allowlist first. If you
   * find yourself writing `{@html}` in another component, you are about to hand
   * an arbitrary instance a script tag in an origin that holds the reader's
   * token. Use this component instead.
   *
   * Foreign HTML in a card is prose: links and mentions get brass and an
   * underline (app.css), and everything the allowlist did not keep is simply
   * gone. Long reviews clamp to 152px with a fade and a button into the detail
   * (4j) — quotations never clamp, because the passage is the whole point.
   */
  import { rich } from '../lib/sanitise.js';

  let { html = '', tone = 'body', clamp = false } = $props();

  const clean = $derived(rich(html));
</script>

{#if clean}
  {#if clamp}
    <div class="clamp">
      <div class="prose {tone}">
        <!-- eslint-disable-next-line svelte/no-at-html-tags -- sanitised above -->
        {@html clean}
      </div>
      <span class="fade" aria-hidden="true"></span>
    </div>
  {:else}
    <div class="prose {tone}">
      <!-- eslint-disable-next-line svelte/no-at-html-tags -- sanitised above -->
      {@html clean}
    </div>
  {/if}
{/if}

<style>
  .prose :global(blockquote) {
    margin: 0.6em 0;
    padding-left: 1em;
    border-left: 2px solid var(--rule);
    color: var(--paper-dim);
  }

  .prose :global(code) {
    font-size: 0.9em;
    background: var(--panel-raised);
    padding: 0.1em 0.3em;
    border-radius: var(--radius);
  }

  .prose :global(pre) {
    overflow-x: auto;
    padding: 0.75em;
    background: var(--panel-raised);
    border-radius: var(--radius);
  }

  .prose :global(ul),
  .prose :global(ol) {
    padding-left: 1.2em;
    margin: 0 0 1em;
  }

  /* Card prose — the default. */
  .body {
    font-size: 1.05rem;
  }

  /* Post detail: the same measure, one step up. */
  .detail {
    font-size: 1.1rem;
  }

  /* A quotation, set large and bright. Never clamped. */
  .quote {
    font-size: 1.55rem;
    line-height: 1.4;
    color: #fbf5e8;
  }

  .small {
    font-size: 0.95rem;
  }

  .clamp {
    position: relative;
    max-height: 152px;
    overflow: hidden;
  }

  .fade {
    position: absolute;
    inset: auto 0 0 0;
    height: 76px;
    background: linear-gradient(rgba(15, 13, 11, 0), var(--ink) 78%);
    pointer-events: none;
  }

  @media (min-width: 44rem) {
    /* Wide screen: the quotation returns to the desktop size (4m). */
    .quote {
      font-size: var(--step-3);
    }
  }
</style>
