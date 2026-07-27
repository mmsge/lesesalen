<script>
  /**
   * The three destinations: the reading room, the filter, the settings.
   *
   * Fixed to the bottom of the screen on a phone, where thumbs are. From 44rem
   * it moves back up into the header and becomes an ordinary sticky nav (4m) —
   * the desktop column never had a bottom bar and does not want one.
   *
   * The filter tab is disabled when there is nothing to filter (4a), and shows
   * how many filters are on when there are any (4e). Disabled here means the
   * real `disabled` attribute: unlike an action button, there is nowhere useful
   * for the tap to go.
   */
  import Icon from './Icon.svelte';
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { tab = 'feed', filters = 0, filterEnabled = true, onselect } = $props();

  const TABS = [
    { id: 'feed', icon: 'shelf', label: 'tab.feed' },
    { id: 'filter', icon: 'filter', label: 'tab.filter' },
    { id: 'settings', icon: 'sliders', label: 'tab.settings' },
  ];
</script>

<nav class="tabs" aria-label={t('nav.sections')}>
  {#each TABS as entry (entry.id)}
    {@const off = entry.id === 'filter' && !filterEnabled}
    <button
      type="button"
      class="tab"
      class:on={tab === entry.id}
      class:off
      disabled={off}
      aria-current={tab === entry.id ? 'page' : undefined}
      onclick={() => onselect?.(entry.id)}
    >
      <Icon name={entry.icon} size={22} />
      <span class="name">
        {t(entry.label)}{#if entry.id === 'filter' && filters} · {formatNumber(filters)}{/if}
      </span>
    </button>
  {/each}
</nav>

<style>
  .tabs {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 15;
    display: flex;
    background: var(--ink-deep);
    border-top: 1px solid var(--rule);
    /* The home indicator sits under this on a modern phone. */
    padding-bottom: calc(12px + var(--safe-bottom));
    padding-top: 8px;
  }

  .tab {
    flex: 1;
    min-height: 48px;
    display: grid;
    justify-items: center;
    align-content: center;
    gap: 3px;
    background: none;
    border: 0;
    padding: 0;
    color: var(--paper-dim);
  }

  .tab.on {
    color: var(--brass);
  }

  .tab.off {
    color: var(--grey-off);
    cursor: default;
  }

  .name {
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }

  /* Wide screen: back into the header, as a sticky row (4m). */
  @media (min-width: 44rem) {
    .tabs {
      position: sticky;
      top: 0;
      bottom: auto;
      width: min(100% - 2.5rem, var(--column));
      margin-inline: auto;
      background: var(--ink);
      border-top: 0;
      border-bottom: 1px solid var(--rule);
      padding: calc(6px + var(--safe-top)) 0 6px;
      justify-content: flex-end;
      gap: 0.5rem;
    }

    .tab {
      flex: 0 0 auto;
      grid-auto-flow: column;
      align-items: center;
      gap: 8px;
      padding: 0 14px;
    }
  }
</style>
