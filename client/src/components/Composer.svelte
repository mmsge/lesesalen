<script>
  /**
   * Replies only (3b) — full screen, over the feed.
   *
   * The post being answered sits at the top **with its cover**, so you can see
   * what you are replying to without leaving the screen. The Mastodon caveat is
   * directly above the field, once and plainly: a reply from here is a Mastodon
   * post that mentions the book post, not a BookWyrm comment, because Mastodon
   * cannot mint BookWyrm objects.
   *
   * Leaving with text in the field asks first. The draft is saved either way —
   * "are you sure" is about leaving the screen, not about destroying what
   * somebody wrote. Offline, the reply is queued with its text intact and shown
   * on the post it belongs to until the network comes back.
   */
  import Icon from './Icon.svelte';
  import Cover from './Cover.svelte';
  import * as mastodon from '../lib/mastodon.js';
  import { enqueue, saveDraft, loadDraft } from '../lib/queue.svelte.js';
  import { net } from '../lib/net.svelte.js';
  import { reportWriteFailure } from '../lib/errors.js';
  import { show } from '../lib/toast.svelte.js';
  import { plain } from '../lib/sanitise.js';
  import { trapFocus } from '../lib/focus.js';
  import { hasProgress } from '../lib/progress.js';
  import { t, formatNumber } from '../lib/i18n.svelte.js';
  import { untrack } from 'svelte';

  let { item, account, onclose } = $props();

  const LIMIT = 4000;
  const VISIBILITIES = ['public', 'unlisted', 'private'];

  // Deliberately one-time defaults, not derived values: the composer is mounted
  // per reply, and once it is on screen the reader owns these fields. `untrack`
  // says so rather than leaving it to be guessed.
  const saved = untrack(() => loadDraft(item.core.uri) || {});
  let text = $state(saved.text || '');
  let warning = $state(saved.warning || '');
  let cwOpen = $state(Boolean(saved.warning));
  let visibility = $state(
    untrack(() => saved.visibility || (item.core.visibility === 'private' ? 'private' : 'public')),
  );
  let sending = $state(false);

  const who = $derived(
    plain(item.core.account?.display_name) || item.core.account?.username || item.core.account?.acct,
  );
  const remaining = $derived(LIMIT - text.length);
  const ready = $derived(Boolean(text.trim()) && remaining >= 0 && !sending);

  /** A line of the parent post, so you remember what you are answering. */
  const excerpt = $derived.by(() => {
    const source =
      item.enrichment.sitat || item.enrichment.tittel || item.enrichment.innhald || item.core.content;
    const words = plain(source);
    if (!words) return item.book?.tittel || '';
    const short = words.length > 96 ? `${words.slice(0, 96)} …` : words;
    return item.enrichment.slag === 'sitat' ? `«${short}»` : short;
  });

  const under = $derived.by(() => {
    if (!item.book?.tittel) return '';
    return hasProgress(item.enrichment)
      ? t('card.sourceWithPage', {
          title: item.book.tittel,
          page: formatNumber(item.enrichment.posisjon),
        })
      : item.book.tittel;
  });

  function keep() {
    saveDraft(item.core.uri, text.trim() ? { text, warning, visibility } : null);
  }

  function leave() {
    keep();
    if (text.trim() && !window.confirm(t('composer.discard'))) return;
    onclose?.();
  }

  async function send(event) {
    event?.preventDefault();
    if (!ready) return;

    // No network: queue it rather than failing, and say so in the reader's own
    // words on the post it belongs to.
    if (!net.online) {
      enqueue({
        id: `${item.core.uri}:${Date.now()}`,
        uri: item.core.uri,
        inReplyToId: item.core.id,
        who,
        text: text.trim(),
        warning: warning.trim(),
        visibility,
        at: Date.now(),
      });
      saveDraft(item.core.uri, null);
      show('composer.queued');
      onclose?.();
      return;
    }

    sending = true;
    try {
      await mastodon.reply(account, {
        inReplyToId: item.core.id,
        text: text.trim(),
        visibility,
        spoilerText: warning.trim(),
      });
      saveDraft(item.core.uri, null);
      show('composer.sent');
      onclose?.();
    } catch (error) {
      reportWriteFailure(error);
    } finally {
      sending = false;
    }
  }

  function cycle() {
    visibility = VISIBILITIES[(VISIBILITIES.indexOf(visibility) + 1) % VISIBILITIES.length];
  }
</script>

<div
  class="composer sheet-enters"
  role="dialog"
  aria-modal="true"
  aria-label={t('composer.replyTo', { name: who })}
  use:trapFocus={leave}
>
  <header>
    <button type="button" class="close" aria-label={t('composer.cancel')} onclick={leave}>
      <Icon name="close" size={20} />
    </button>
    <h2>{t('composer.replyTo', { name: who })}</h2>
  </header>

  <form onsubmit={send}>
    <div class="parent">
      {#if item.book}<Cover book={item.book} width={40} />{/if}
      <div class="what">
        <p class="excerpt">{excerpt}</p>
        {#if under}<p class="under">{under}</p>{/if}
      </div>
    </div>

    <p class="caveat">{t('composer.caveat')}</p>

    {#if cwOpen}
      <label class="cw">
        <span class="visually-hidden">{t('composer.contentWarning')}</span>
        <input
          type="text"
          bind:value={warning}
          placeholder={t('composer.contentWarning')}
          maxlength="180"
        />
      </label>
    {/if}

    <label class="field">
      <span class="visually-hidden">{t('composer.placeholder')}</span>
      <textarea bind:value={text} placeholder={t('composer.placeholder')} rows="5"></textarea>
    </label>

    <div class="row">
      <button type="button" class="pill" onclick={cycle}>
        <Icon name="globe" size={16} />
        {t(`composer.visibility${visibility === 'public' ? 'Public' : visibility === 'unlisted' ? 'Unlisted' : 'Private'}`)}
      </button>
      <button
        type="button"
        class="pill"
        class:on={cwOpen}
        aria-pressed={cwOpen}
        onclick={() => (cwOpen = !cwOpen)}
      >
        {t('composer.warning')}
      </button>
      <span class="count" class:over={remaining < 0} aria-live="polite">
        {formatNumber(remaining)}
      </span>
    </div>

    <button type="submit" class="primary send" disabled={!ready}>
      {#if sending}<span class="spinner" aria-hidden="true"></span>{/if}
      {sending ? t('composer.sending') : net.online ? t('composer.send') : t('composer.queue')}
    </button>
  </form>
</div>

<style>
  .composer {
    position: fixed;
    inset: 0;
    z-index: 35;
    display: flex;
    flex-direction: column;
    background: var(--ink);
  }

  header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: calc(14px + var(--safe-top)) 20px 14px;
    border-bottom: 1px solid var(--rule);
  }

  .close {
    flex: none;
    width: 44px;
    height: 44px;
    margin-left: -10px;
    display: grid;
    place-items: center;
    background: none;
    border: 0;
    color: var(--paper-dim);
  }

  h2 {
    margin: 0;
    font-size: 1.15rem;
    color: var(--paper-bright);
  }

  form {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    width: min(100%, var(--column));
    margin-inline: auto;
    padding: 16px 20px calc(20px + var(--safe-bottom));
    background: radial-gradient(110% 60% at 50% 0, rgba(201, 162, 39, 0.1), rgba(15, 13, 11, 0) 65%);
  }

  .parent {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--rule);
  }

  .what {
    min-width: 0;
  }

  .excerpt {
    margin: 0;
    font-family: var(--serif);
    font-size: 0.95rem;
    line-height: 1.5;
    color: var(--paper-dim);
  }

  .under {
    margin: 4px 0 0;
    font-size: 0.78rem;
    color: var(--paper-dim);
  }

  .caveat {
    margin: 14px 0 12px;
    padding-left: 12px;
    border-left: 2px solid var(--rule);
    font-size: 0.85rem;
    color: var(--paper-dim);
  }

  .cw input {
    width: 100%;
    min-height: 44px;
    margin-bottom: 10px;
    font: inherit;
    color: var(--paper);
    background: var(--panel);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 0 12px;
  }

  .field {
    display: block;
  }

  textarea {
    width: 100%;
    min-height: 150px;
    font: inherit;
    font-family: var(--serif);
    font-size: 1.1rem;
    line-height: 1.6;
    color: var(--paper-bright);
    background: var(--panel);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 12px 14px;
    resize: vertical;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 12px;
    flex-wrap: wrap;
  }

  .pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-height: 44px;
    padding: 0 14px;
    background: none;
    border: 1px solid var(--rule);
    border-radius: 999px;
    color: var(--paper-dim);
    font-size: 0.85rem;
  }

  .pill.on {
    background: rgba(201, 162, 39, 0.14);
    border-color: var(--brass);
    color: var(--brass);
  }

  .count {
    margin-left: auto;
    font-size: 0.8rem;
    color: var(--paper-dim);
    font-variant-numeric: tabular-nums;
  }

  .count.over {
    color: var(--warn);
  }

  .send {
    margin-top: 14px;
    min-height: 50px;
    font-size: 1rem;
  }

  .spinner {
    display: inline-block;
    width: 13px;
    height: 13px;
    border-radius: 999px;
    border: 1.5px solid var(--ink);
    border-top-color: transparent;
    animation: lampSpin 0.7s linear infinite;
  }
</style>
