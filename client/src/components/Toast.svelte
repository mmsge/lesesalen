<script>
  /**
   * One toast, above the tab bar. A new one replaces the previous rather than
   * stacking — see lib/toast.svelte.js.
   *
   * `role="status"` rather than `alert`: none of these interrupt anything, and
   * an assertive announcement for "the link is copied" is rude.
   */
  import { toast } from '../lib/toast.svelte.js';
  import { t } from '../lib/i18n.svelte.js';
</script>

<div class="live" role="status" aria-live="polite">
  {#if toast.message}
    <p class="toast enters" class:warn={toast.tone === 'warn'}>{t(toast.message)}</p>
  {/if}
</div>

<style>
  .live {
    position: fixed;
    left: 16px;
    right: 16px;
    bottom: calc(80px + var(--safe-bottom));
    z-index: 40;
    pointer-events: none;
  }

  .toast {
    margin: 0 auto;
    max-width: var(--column);
    padding: 11px 14px;
    border-radius: var(--radius);
    font-size: 0.88rem;
    background: var(--panel);
    border: 1px solid var(--rule);
    color: var(--paper);
    box-shadow: 0 12px 26px rgba(0, 0, 0, 0.6);
  }

  .toast.warn {
    border-color: var(--warn-rule);
    color: var(--warn);
  }
</style>
