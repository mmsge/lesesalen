<script>
  /**
   * Content warnings, as a hatch rather than a blank (4i).
   *
   * A hatched panel says "there is something here" where an empty box says
   * "this post is broken". The warning text is never covered — it sits legibly
   * on the hatch, because it is the one thing the reader needs in order to
   * decide. After revealing, the warning stays as a line you can fold the post
   * back into.
   *
   * `spoiler_text` is plain text in the API and is escaped, never parsed. Only
   * the prose is hidden: the book, the title and the rating stay visible,
   * because the prose is the spoiler.
   */
  import Icon from './Icon.svelte';
  import { prefs } from '../lib/prefs.svelte.js';
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { warning = '', paragraphs = 1, children } = $props();

  // null = follow the reader's setting; true/false = this card, this session.
  let override = $state(null);
  const shown = $derived(override ?? prefs.cwOpen);
</script>

{#if shown}
  <div class="revealed">
    <span class="eye"><Icon name="shown" size={16} /></span>
    <span class="warning">{warning || t('card.contentWarning')}</span>
    <button type="button" class="fold" onclick={(event) => { event.stopPropagation(); override = false; }}>
      {t('spoiler.hide')}
    </button>
  </div>
  {@render children?.()}
{:else}
  <button
    type="button"
    class="hatch"
    onclick={(event) => { event.stopPropagation(); override = true; }}
  >
    <span class="eye"><Icon name="hidden" size={18} /></span>
    <span class="text">
      <span class="warning">{warning || t('card.contentWarning')}</span>
      <span class="hint">{t('spoiler.reveal', { n: formatNumber(paragraphs) })}</span>
    </span>
  </button>
{/if}

<style>
  /* The hatch itself: visibly occupied, not empty. */
  .hatch {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    min-height: 52px;
    padding: 10px 14px;
    text-align: left;
    background: repeating-linear-gradient(135deg, #17140f 0 8px, #1c1811 8px 16px);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
  }

  .hatch .eye {
    color: var(--brass);
  }

  .text {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 2px;
  }

  .hatch .warning {
    font-size: 0.92rem;
    color: var(--paper);
  }

  .hint {
    font-size: 0.8rem;
    color: var(--paper-dim);
  }

  /* Once revealed it stays as a line you can fold back. */
  .revealed {
    display: flex;
    align-items: center;
    gap: 10px;
    min-height: 44px;
    margin-bottom: 12px;
    padding: 4px 12px;
    background: var(--panel);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    color: var(--paper-dim);
  }

  .revealed .warning {
    flex: 1;
    min-width: 0;
    font-size: 0.84rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .fold {
    flex: none;
    min-height: 44px;
    padding: 0 8px;
    background: none;
    border: 0;
    color: var(--brass);
    font-size: 0.82rem;
  }
</style>
