<script>
  /**
   * Two notices that sit above the shelf and never replace it.
   *
   * **Sweeping (4b):** a brass hairline under the header with a figure beside
   * it, not a blocking screen. The feed fills as shelves land, and posts arrive
   * complete rather than half-drawn.
   *
   * **Partial failure (4c):** the hosts that did not answer, what happened to
   * each, and a retry. A rate limit counts down from the instance's own
   * `Retry-After`; without one we say five minutes and "om lag", because a
   * precise number we invented would be a lie with a colon in it.
   *
   * Partial failure is never blocking. The rest of the shelf is complete and
   * the reader can carry on reading while these wait.
   */
  import { clock } from '../lib/errors.js';
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { sweeping = false, done = 0, total = 0, failures = [], unreadable = 0, onretry } = $props();

  const percent = $derived(total ? Math.round((done / total) * 100) : 0);

  // Recomputed once a second only while a countdown is on screen.
  let now = $state(Date.now());
  $effect(() => {
    if (!failures.some((entry) => entry.until)) return;
    const timer = setInterval(() => (now = Date.now()), 1000);
    return () => clearInterval(timer);
  });

  function words(entry) {
    if (entry.kind === 'tidsavbrot') return t('sweep.timeout', { host: entry.host });
    if (entry.kind === 'grense') {
      const minutes = Math.max(1, Math.ceil((entry.seconds || 300) / 60));
      return entry.exact
        ? t('sweep.rateLimit', { host: entry.host, min: formatNumber(minutes) })
        : t('sweep.rateLimitVague', { host: entry.host, min: formatNumber(minutes) });
    }
    return t('sweep.failed', { host: entry.host });
  }
</script>

{#if sweeping}
  <div class="sweep">
    <div class="line">
      <span class="what">
        {t('sweep.progress', { done: formatNumber(done), total: formatNumber(total) })}
      </span>
      <span class="percent">{formatNumber(percent)} %</span>
    </div>
    <!-- The figure above is the accessible version of this bar; under
         prefers-reduced-motion the bar simply stops easing. -->
    <span
      class="track"
      role="progressbar"
      aria-valuenow={percent}
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <span class="fill" style:width={`${percent}%`}></span>
    </span>
    <p class="note">{t('sweep.note')}</p>
  </div>
{/if}

{#if failures.length || unreadable}
  <div class="missing">
    {#if failures.length}
      <p class="label heading">{t('sweep.missing', { n: formatNumber(failures.length) })}</p>
      <ul>
        {#each failures as entry (entry.host)}
          <li>
            <span class="dot" aria-hidden="true"></span>
            <span class="host">{words(entry)}</span>
            {#if entry.until}
              <span class="countdown">{clock((entry.until - now) / 1000)}</span>
            {:else}
              <button type="button" class="retry" onclick={() => onretry?.(entry)}>
                {t('sweep.retry')}
              </button>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
    {#if unreadable}
      <p class="note">{t('sweep.unreadable', { n: formatNumber(unreadable) })}</p>
    {/if}
    <p class="note">{t('sweep.rest')}</p>
  </div>
{/if}

<style>
  .sweep {
    width: min(100%, var(--column));
    margin-inline: auto;
    padding: 4px 20px 18px;
  }

  .line {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
  }

  .what {
    font-size: 0.9rem;
    color: var(--paper);
  }

  .percent {
    font-size: 0.8rem;
    color: var(--paper-dim);
    font-variant-numeric: tabular-nums;
  }

  .track {
    display: block;
    height: 3px;
    background: var(--rule);
    border-radius: 2px;
    overflow: hidden;
  }

  .fill {
    display: block;
    height: 100%;
    background: var(--brass);
    box-shadow: 0 0 12px rgba(201, 162, 39, 0.8);
  }

  @media (prefers-reduced-motion: no-preference) {
    .fill {
      transition: width 0.3s ease;
    }
  }

  .missing {
    width: min(100% - 40px, var(--column));
    margin: 0 auto 4px;
    padding: 14px 16px;
    background: var(--panel);
    border: 1px solid var(--rule);
    border-left: 2px solid var(--warn-rule);
    border-radius: var(--radius);
  }

  .heading {
    margin-bottom: 4px;
    color: var(--warn);
    letter-spacing: 0.16em;
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 8px;
    font-size: 0.85rem;
    color: var(--paper-dim);
  }

  li {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .dot {
    flex: none;
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: var(--warn-rule);
  }

  .host {
    flex: 1;
    min-width: 0;
  }

  .retry {
    flex: none;
    min-height: 44px;
    padding: 0 14px;
    background: none;
    border: 1px solid var(--rule);
    border-radius: 999px;
    color: var(--brass);
    font-size: 0.82rem;
  }

  .countdown {
    flex: none;
    font-size: 0.8rem;
    color: var(--paper-dim);
    font-variant-numeric: tabular-nums;
  }

  .note {
    margin: 10px 0 0;
    font-size: 0.82rem;
    color: var(--paper-dim);
  }
</style>
