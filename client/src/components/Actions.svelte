<script>
  /**
   * Reply, favourite, boost — all through the Mastodon API, from the browser.
   *
   * Favourite and boost work exactly as they do in any Mastodon client. Reply
   * opens the composer, which says plainly that a reply is a Mastodon post and
   * not a BookWyrm comment.
   */
  import * as mastodon from '../lib/mastodon.js';
  import { t } from '../lib/i18n.svelte.js';

  let { item, account = null, onreply = null } = $props();

  // Overrides rather than copies of the status fields: null means "whatever the
  // status says", and a toggle sets the override optimistically. Copying the
  // initial value into $state would freeze it if the item were ever replaced.
  let favouriteOverride = $state(null);
  let boostOverride = $state(null);
  let busy = $state(false);

  const favourited = $derived(favouriteOverride ?? Boolean(item.core.favourited));
  const boosted = $derived(boostOverride ?? Boolean(item.core.reblogged));

  async function toggleFavourite() {
    if (!account || busy || item.demo) return;
    busy = true;
    const next = !favourited;
    favouriteOverride = next; // optimistic; reverted if the instance disagrees
    try {
      await mastodon.favourite(account, item.core.id, next);
    } catch {
      favouriteOverride = !next;
    } finally {
      busy = false;
    }
  }

  async function toggleBoost() {
    if (!account || busy || item.demo) return;
    busy = true;
    const next = !boosted;
    boostOverride = next;
    try {
      await mastodon.boost(account, item.core.id, next);
    } catch {
      boostOverride = !next;
    } finally {
      busy = false;
    }
  }
</script>

<div class="actions">
  <button type="button" onclick={() => onreply?.(item)} disabled={!account || item.demo}>
    {t('action.replyTo')}
  </button>
  <button
    type="button"
    class:on={favourited}
    onclick={toggleFavourite}
    disabled={!account || item.demo}
    aria-pressed={favourited}
  >
    {favourited ? t('action.unfavourite') : t('action.favourite')}
  </button>
  <button
    type="button"
    class:on={boosted}
    onclick={toggleBoost}
    disabled={!account || item.demo}
    aria-pressed={boosted}
  >
    {boosted ? t('action.unboost') : t('action.boost')}
  </button>
</div>

<style>
  .actions {
    display: flex;
    gap: 0.5em;
    margin-top: 0.9em;
    padding-top: 0.7em;
    border-top: 1px solid var(--rule);
  }

  button {
    background: none;
    border: 1px solid transparent;
    border-radius: var(--radius);
    padding: 0.2em 0.6em;
    font-size: 0.82rem;
    color: var(--paper-dim);
  }

  button:hover:not(:disabled) {
    color: var(--paper);
    border-color: var(--rule);
  }

  button.on {
    color: var(--brass);
    border-color: var(--brass);
  }

  button:disabled {
    opacity: 0.4;
    cursor: default;
  }
</style>
