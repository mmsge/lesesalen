<script>
  /**
   * The bottom shelf (4d).
   *
   * How far back you have read, and an outlined brass button to go further. The
   * button is outline rather than filled on purpose: it must not compete with
   * the posts above it. While it is fetching, the plate stays and a round
   * counter says which round it is on — a figure, so it still says something
   * under prefers-reduced-motion.
   */
  import { t, formatNumber, formatDate } from '../lib/i18n.svelte.js';

  let {
    posts = 0,
    reach = null,
    loading = false,
    exhausted = false,
    shelves = 0,
    disabled = false,
    onmore,
  } = $props();
</script>

<div class="rail dim"></div>

<div class="tail">
  <p class="label dim">{t('tail.bottom')}</p>

  {#if reach}
    <p class="read">
      {t('tail.read', { n: formatNumber(posts), date: formatDate(reach) })}
    </p>
  {/if}

  {#if loading}
    <div class="working">
      <span class="spinner" aria-hidden="true"></span>
      <span>{t('tail.fetching')}</span>
    </div>
  {:else if exhausted}
    <p class="note">{t('tail.end', { count: formatNumber(shelves) })}</p>
  {:else}
    <button type="button" class="more" onclick={() => onmore?.()} {disabled}>
      {t('tail.more')}
    </button>
    <p class="note">{t('tail.help')}</p>
  {/if}
</div>

<style>
  .tail {
    width: min(100%, var(--column));
    margin-inline: auto;
    padding: 24px 22px 26px;
    text-align: center;
    background: radial-gradient(90% 100% at 50% 100%, rgba(201, 162, 39, 0.1), rgba(15, 13, 11, 0) 65%);
  }

  .label {
    margin-bottom: 4px;
  }

  .read {
    margin: 0 0 16px;
    font-size: 0.9rem;
    color: var(--paper);
  }

  .more {
    width: 100%;
    min-height: 50px;
    background: none;
    border: 1px solid var(--brass);
    border-radius: var(--radius);
    color: var(--brass);
    font-size: 1rem;
    font-weight: 600;
  }

  .more:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .note {
    margin: 12px 0 0;
    font-size: 0.85rem;
    color: var(--paper-dim);
  }

  .working {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    min-height: 50px;
    font-size: 0.85rem;
    color: var(--paper-dim);
  }

  .spinner {
    width: 11px;
    height: 11px;
    border-radius: 999px;
    border: 1.5px solid var(--brass);
    border-top-color: transparent;
    animation: lampSpin 0.7s linear infinite;
  }
</style>
