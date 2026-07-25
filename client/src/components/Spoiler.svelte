<script>
  /**
   * Content warnings.
   *
   * `spoiler_text` is plain text in the API and is escaped, never parsed. The
   * body blurs with the first line legible above it, and stays hidden until the
   * reader asks — the state is per card and does not persist.
   */
  import { t } from '../lib/i18n.svelte.js';

  let { warning = '', children } = $props();

  let revealed = $state(false);
</script>

<div class="spoiler">
  <div class="head">
    <span class="label">{t('card.contentWarning')}</span>
    {#if warning}<span class="text">{warning}</span>{/if}
    <button type="button" onclick={() => (revealed = !revealed)}>
      {revealed ? t('card.hideContent') : t('card.showContent')}
    </button>
  </div>
  <div class="body" class:hidden={!revealed} aria-hidden={!revealed}>
    {@render children?.()}
  </div>
</div>

<style>
  .spoiler {
    display: grid;
    gap: 0.6em;
  }

  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.5em;
    font-size: 0.88rem;
  }

  .label {
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    color: var(--oxblood);
    border: 1px solid var(--oxblood);
    border-radius: var(--radius);
    padding: 0.1em 0.45em;
  }

  .text {
    color: var(--paper);
    font-family: var(--serif);
  }

  button {
    margin-left: auto;
    background: none;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 0.15em 0.6em;
    color: var(--paper-dim);
    font-size: 0.82rem;
  }

  button:hover {
    color: var(--paper);
    border-color: var(--brass);
  }

  .body.hidden {
    /* Blurred rather than removed: the shape of the post stays, so a run of
       warned posts does not make the column jump when they are revealed. */
    filter: blur(7px);
    opacity: 0.55;
    pointer-events: none;
    user-select: none;
    max-height: 5.5rem;
    overflow: hidden;
  }
</style>
