<script>
  /**
   * Reply, favourite, boost — all through the Mastodon API, from the browser.
   *
   * Favourite and boost work exactly as they do in any Mastodon client. Reply
   * opens the composer, which says plainly that a reply is a Mastodon post and
   * not a BookWyrm comment.
   *
   * A post collected from an outbox has no Mastodon status id, because an outbox
   * knows nothing about the reader's instance. So the id is resolved on the first
   * interaction with the card and not before: eager resolution would be one
   * federated fetch per card, paid for by the reader's own server (ADR 0008).
   *
   * If the reader's instance simply does not have the post and cannot fetch it,
   * the action is not available. Saying so by disabling the button is better than
   * a failure that looks like a bug.
   */
  import * as mastodon from '../lib/mastodon.js';
  import { resolve } from '../lib/collection.svelte.js';
  import { t } from '../lib/i18n.svelte.js';

  let { item, account = null, onreply = null } = $props();

  // Overrides rather than copies of the status fields: null means "whatever the
  // status says", and a toggle sets the override optimistically. Copying the
  // initial value into $state would freeze it if the item were ever replaced.
  let favouriteOverride = $state(null);
  let boostOverride = $state(null);
  let busy = $state(false);
  let unreachable = $state(false);

  const favourited = $derived(favouriteOverride ?? Boolean(item.core.favourited));
  const boosted = $derived(boostOverride ?? Boolean(item.core.reblogged));
  const disabled = $derived(!account || item.demo || unreachable);

  /** The local status id, resolving it first if this card has never needed one. */
  async function statusId() {
    if (item.core.id) return item.core.id;
    const found = await resolve(account, item);
    if (!found) unreachable = true;
    return found;
  }

  async function toggleFavourite() {
    if (disabled || busy) return;
    busy = true;
    try {
      const id = await statusId();
      if (!id) return;
      const next = !favourited;
      favouriteOverride = next; // optimistic; reverted if the instance disagrees
      try {
        await mastodon.favourite(account, id, next);
      } catch {
        favouriteOverride = !next;
      }
    } finally {
      busy = false;
    }
  }

  async function toggleBoost() {
    if (disabled || busy) return;
    busy = true;
    try {
      const id = await statusId();
      if (!id) return;
      const next = !boosted;
      boostOverride = next;
      try {
        await mastodon.boost(account, id, next);
      } catch {
        boostOverride = !next;
      }
    } finally {
      busy = false;
    }
  }

  /** Replying needs the id too — the composer posts `in_reply_to_id`. */
  async function startReply() {
    if (disabled || busy) return;
    busy = true;
    try {
      if (await statusId()) onreply?.(item);
    } finally {
      busy = false;
    }
  }
</script>

<div class="actions">
  <button type="button" onclick={startReply} disabled={disabled || busy}>
    {t('action.replyTo')}
  </button>
  <button
    type="button"
    class:on={favourited}
    onclick={toggleFavourite}
    disabled={disabled || busy}
    aria-pressed={favourited}
  >
    {favourited ? t('action.unfavourite') : t('action.favourite')}
  </button>
  <button
    type="button"
    class:on={boosted}
    onclick={toggleBoost}
    disabled={disabled || busy}
    aria-pressed={boosted}
  >
    {boosted ? t('action.unboost') : t('action.boost')}
  </button>
  {#if unreachable}
    <span class="note">{t('action.notOnYourInstance')}</span>
  {/if}
</div>

<style>
  .actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5em;
    margin-top: 0.9em;
    padding-top: 0.7em;
    border-top: 1px solid var(--rule);
  }

  .note {
    font-size: 0.78rem;
    color: var(--paper-dim);
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
