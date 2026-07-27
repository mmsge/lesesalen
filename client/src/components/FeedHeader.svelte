<script>
  /**
   * The app name on a lamp wash, and one word about the state of the shelf.
   *
   * That right-hand word is the whole status indicator: "12 hyller" normally,
   * "10 av 12" when hosts are missing, "Hentar" mid-sweep, "Frå samlinga" when
   * the session has expired, and a grey dot plus "Utan nett" when there is no
   * network. Never an error screen — the shelf still shows what arrived.
   */
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { shelves = 0, reached = 0, sweeping = false, expired = false, offline = false } = $props();
</script>

<header>
  <div class="inner">
    <span class="name">{t('app.name')}</span>

    {#if offline}
      <span class="state offline"><span class="dot" aria-hidden="true"></span>{t('state.offline')}</span>
    {:else if expired}
      <span class="state warn">{t('state.fromCollection')}</span>
    {:else if sweeping}
      <span class="state busy">{t('state.fetching')}</span>
    {:else if reached && reached < shelves}
      <span class="state">{t('state.someShelves', {
        done: formatNumber(reached),
        total: formatNumber(shelves),
      })}</span>
    {:else}
      <span class="state">{t('state.shelves', { n: formatNumber(shelves) })}</span>
    {/if}
  </div>
</header>

<style>
  header {
    padding: calc(18px + var(--safe-top)) 20px 12px;
    background: radial-gradient(80% 130% at 50% -20%, rgba(201, 162, 39, 0.24), transparent 70%);
  }

  .inner {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    width: min(100%, var(--column));
    margin-inline: auto;
  }

  .name {
    font-family: var(--serif);
    font-weight: 600;
    font-size: 1.3rem;
    line-height: 1.2;
    color: var(--paper-bright);
  }

  .state {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--paper-dim);
    white-space: nowrap;
  }

  .state.busy {
    color: var(--brass);
  }

  .state.warn {
    color: var(--warn);
  }

  /* Never colour alone: the dot always has "Utan nett" next to it. */
  .dot {
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: var(--grey-off);
  }
</style>
