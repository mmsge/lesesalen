<script>
  /**
   * Reply, favourite, boost — all through the Mastodon API, from the browser.
   *
   * Five states per button (4m), and every one of them is visible rather than
   * inferred: off, on, sending, failed, logged out. Each target is at least
   * 44×44 with a Nynorsk `aria-label` and `aria-pressed` on the toggles.
   *
   * Favourite and boost are **optimistic**: the button flips immediately, spins
   * while the request is in flight, and rolls back with a warn border for 2.6 s
   * plus a toast if the instance disagrees.
   *
   * A post collected from an outbox has no Mastodon status id, because an outbox
   * knows nothing about the reader's instance. So the id is resolved on the first
   * interaction with the card and not before: eager resolution would be one
   * federated fetch per card, paid for by the reader's own server (ADR 0008).
   *
   * When there is no session the buttons stay on screen at 40 % and carry
   * `aria-disabled` rather than `disabled` — a tap has to be able to land, so it
   * can take the reader to the login instead of doing nothing at all.
   */
  import Icon from './Icon.svelte';
  import * as mastodon from '../lib/mastodon.js';
  import { resolve, feed, drop } from '../lib/collection.svelte.js';
  import { reportWriteFailure } from '../lib/errors.js';
  import { net } from '../lib/net.svelte.js';
  import { navigate } from '../lib/router.svelte.js';
  import { t } from '../lib/i18n.svelte.js';

  let { item, account = null, onreply = null, big = false } = $props();

  const FAIL_MS = 2600;

  // Overrides rather than copies of the status fields: null means "whatever the
  // status says", and a toggle sets the override optimistically. Copying the
  // initial value into $state would freeze it if the item were ever replaced.
  let favouriteOverride = $state(null);
  let boostOverride = $state(null);
  let pending = $state({ fav: false, boost: false });
  let failed = $state({ fav: false, boost: false });
  let unreachable = $state(false);

  const favourited = $derived(favouriteOverride ?? Boolean(item.core.favourited));
  const boosted = $derived(boostOverride ?? Boolean(item.core.reblogged));
  // Reading never stops; writing does. An expired session, no session at all,
  // no network, or a post the reader's instance simply cannot see.
  const locked = $derived(!account || item.demo || feed.expired || !net.online || unreachable);

  function markFailed(which) {
    failed[which] = true;
    setTimeout(() => {
      failed[which] = false;
    }, FAIL_MS);
  }

  /** The local status id, resolving it first if this card has never needed one. */
  async function statusId() {
    if (item.core.id) return item.core.id;
    const found = await resolve(account, item);
    if (!found) unreachable = true;
    return found;
  }

  async function toggle(which) {
    if (locked) {
      // Not a dead end: say what the reader can do about it.
      if (!account || feed.expired) navigate('/logg-inn');
      return;
    }
    if (pending[which]) return;

    const on = which === 'fav' ? favourited : boosted;
    const next = !on;
    const set = (value) => {
      if (which === 'fav') favouriteOverride = value;
      else boostOverride = value;
    };

    pending[which] = true;
    set(next); // optimistic; rolled back below if the instance disagrees
    try {
      const id = await statusId();
      if (!id) throw new Error('unreachable');
      if (which === 'fav') await mastodon.favourite(account, id, next);
      else await mastodon.boost(account, id, next);
    } catch (error) {
      set(on);
      if (reportWriteFailure(error) === 'gone') drop(item);
      else markFailed(which);
    } finally {
      pending[which] = false;
    }
  }

  /** Replying needs the id too — the composer posts `in_reply_to_id`. */
  async function startReply() {
    if (!account || feed.expired) {
      navigate('/logg-inn');
      return;
    }
    // Offline replies are queued with their text intact, so the composer opens
    // whether or not there is a network to send through.
    if (!net.online) {
      onreply?.(item);
      return;
    }
    if (await statusId()) onreply?.(item);
  }
</script>

<div class="actions" class:big>
  {#if big}
    <button type="button" class="wide" onclick={startReply} aria-disabled={locked && !net.online ? undefined : locked}>
      <Icon name="reply" size={20} />
      {t('action.replyTo')}
    </button>
  {:else}
    <button
      type="button"
      class="icon"
      aria-label={t('action.replyTo')}
      aria-disabled={locked && net.online ? true : undefined}
      onclick={(event) => {
        event.stopPropagation();
        startReply();
      }}
    >
      <Icon name="reply" size={20} />
    </button>
  {/if}

  <button
    type="button"
    class="icon toggle"
    class:on={favourited}
    class:failed={failed.fav}
    aria-label={favourited ? t('action.unfavourite') : t('action.favourite')}
    aria-pressed={favourited}
    aria-disabled={locked ? true : undefined}
    onclick={(event) => {
      event.stopPropagation();
      toggle('fav');
    }}
  >
    {#if pending.fav}
      <span class="spinner" aria-hidden="true"></span>
      <span class="visually-hidden">{t('action.sending')}</span>
    {:else if failed.fav}
      <span class="bang"><Icon name="bang" size={18} /></span>
      <span class="visually-hidden">{t('error.writeFailed')}</span>
    {:else}
      <span class="lozenge" class:filled={favourited} aria-hidden="true"></span>
    {/if}
  </button>

  <button
    type="button"
    class="icon toggle"
    class:on={boosted}
    class:failed={failed.boost}
    aria-label={boosted ? t('action.unboost') : t('action.boost')}
    aria-pressed={boosted}
    aria-disabled={locked ? true : undefined}
    onclick={(event) => {
      event.stopPropagation();
      toggle('boost');
    }}
  >
    {#if pending.boost}
      <span class="spinner" aria-hidden="true"></span>
      <span class="visually-hidden">{t('action.sending')}</span>
    {:else if failed.boost}
      <span class="bang"><Icon name="bang" size={18} /></span>
      <span class="visually-hidden">{t('error.writeFailed')}</span>
    {:else}
      <Icon name="boost" size={20} />
    {/if}
  </button>

  {#if big}
    <button
      type="button"
      class="icon"
      aria-label={t('action.share')}
      onclick={() => onreply?.(item, 'share')}
    >
      <Icon name="share" size={20} />
    </button>
  {/if}

  {#if unreachable}
    <span class="note">{t('action.notOnYourInstance')}</span>
  {/if}
</div>

<style>
  .actions {
    display: flex;
    align-items: center;
    gap: 2px;
  }

  .actions.big {
    gap: 6px;
  }

  button {
    display: grid;
    place-items: center;
    background: none;
    border: 1px solid transparent;
    border-radius: var(--radius);
    color: var(--paper-dim);
    padding: 0;
  }

  /* Every icon target clears 44×44; the detail bar's are 48. */
  .icon {
    flex: none;
    width: 44px;
    height: 44px;
  }

  .big .icon {
    width: 48px;
    height: 48px;
    border-color: var(--rule);
  }

  .wide {
    flex: 1;
    min-height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border-color: var(--rule);
    color: var(--paper);
    font-size: 0.9rem;
  }

  /* On: the icon, the border and a faint brass wash. */
  .toggle.on {
    color: var(--brass);
    border-color: var(--brass);
    background: rgba(201, 162, 39, 0.14);
  }

  /* Failed: a warn border and an exclamation, for 2.6 s. */
  .toggle.failed {
    border-color: var(--warn-rule);
    background: none;
  }

  .bang {
    display: grid;
    color: var(--warn);
  }

  /* Logged out, expired or offline: visible, dimmed, and still tappable so it
     can lead somewhere. */
  button[aria-disabled='true'] {
    opacity: 0.4;
    cursor: default;
  }

  .lozenge {
    display: inline-block;
    width: 13px;
    height: 13px;
    transform: rotate(45deg);
    border: 1.4px solid currentColor;
    border-radius: 1px;
  }

  .lozenge.filled {
    background: var(--brass);
    border-color: var(--brass);
  }

  .spinner {
    display: inline-block;
    width: 13px;
    height: 13px;
    border-radius: 999px;
    border: 1.5px solid var(--brass);
    border-top-color: transparent;
    animation: lampSpin 0.7s linear infinite;
  }

  .note {
    font-size: 0.78rem;
    color: var(--paper-dim);
  }
</style>
