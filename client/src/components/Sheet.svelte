<script>
  /**
   * A sheet from the bottom, over whatever was there.
   *
   * Every sheet in the app is a history entry, so the back button closes it and
   * leaves the view underneath exactly as it was (§Back button). It traps focus
   * while it is open, closes on Escape, and clears the home indicator with
   * `padding-bottom: calc(12px + env(safe-area-inset-bottom))`.
   */
  import { trapFocus } from '../lib/focus.js';
  import { t } from '../lib/i18n.svelte.js';

  let { onclose, label = '', blur = false, children } = $props();
</script>

<div class="sheet-layer" class:blur>
  <button type="button" class="scrim" aria-label={t('sheet.close')} onclick={() => onclose?.()}
  ></button>

  <div
    class="sheet sheet-enters"
    role="dialog"
    aria-modal="true"
    aria-label={label}
    use:trapFocus={onclose}
  >
    <span class="grip" aria-hidden="true"></span>
    {@render children?.()}
  </div>
</div>

<style>
  .sheet-layer {
    position: fixed;
    inset: 0;
    z-index: 30;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
  }

  .scrim {
    position: absolute;
    inset: 0;
    background: rgba(11, 10, 9, 0.72);
    border: 0;
    padding: 0;
    animation: lampFade 0.2s ease both;
  }

  /* The filter sheet sits over a blurred feed; the book sheet does not. */
  .blur .scrim {
    backdrop-filter: blur(6px);
  }

  .sheet {
    position: relative;
    width: min(100%, var(--column));
    margin-inline: auto;
    max-height: 92vh;
    overflow-y: auto;
    background: linear-gradient(var(--panel), var(--ink));
    border-top: 1px solid rgba(201, 162, 39, 0.45);
    box-shadow: 0 -20px 40px rgba(0, 0, 0, 0.78);
    padding: 10px 20px calc(12px + var(--safe-bottom));
  }

  .grip {
    display: block;
    width: 46px;
    height: 4px;
    border-radius: 999px;
    background: var(--rule);
    margin: 0 auto 16px;
  }

  /* Wide screen: a panel over the feed rather than a sheet from the bottom (4m). */
  @media (min-width: 44rem) {
    .sheet-layer {
      justify-content: center;
      padding: 2rem 1.25rem;
    }

    .sheet {
      max-height: 80vh;
      border: 1px solid var(--rule);
      border-top-color: rgba(201, 162, 39, 0.45);
      border-radius: var(--radius);
      padding-bottom: 20px;
    }
  }
</style>
