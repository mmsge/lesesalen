<script>
  /**
   * The ONLY place in this app that is allowed to use `{@html}`.
   *
   * Everything passed here goes through the DOMPurify allowlist first. If you
   * find yourself writing `{@html}` in another component, you are about to hand
   * an arbitrary instance a script tag in an origin that holds the reader's
   * token. Use this component instead.
   */
  import { rich } from '../lib/sanitise.js';

  let { html = '', tone = 'body' } = $props();

  const clean = $derived(rich(html));
</script>

{#if clean}
  <div class="prose" class:quote={tone === 'quote'} class:small={tone === 'small'}>
    <!-- eslint-disable-next-line svelte/no-at-html-tags -- sanitised above -->
    {@html clean}
  </div>
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
    background: var(--ink-700);
    padding: 0.1em 0.3em;
    border-radius: var(--radius);
  }

  .prose :global(pre) {
    overflow-x: auto;
    padding: 0.75em;
    background: var(--ink-700);
    border-radius: var(--radius);
  }

  .prose :global(ul),
  .prose :global(ol) {
    padding-left: 1.2em;
    margin: 0 0 0.85em;
  }

  .quote {
    font-size: var(--step-3);
    line-height: 1.35;
    max-width: none;
  }

  .small {
    font-size: var(--step-0);
  }
</style>
