<script>
  /**
   * Replies only.
   *
   * Mastodon cannot mint BookWyrm objects, so a reply from here is a Mastodon
   * post that mentions the book post — not a BookWyrm comment. The caveat sits
   * right next to the field, once and plainly, so nobody finds out afterwards.
   */
  import { untrack } from 'svelte';
  import * as mastodon from '../lib/mastodon.js';
  import { plain } from '../lib/sanitise.js';
  import { t } from '../lib/i18n.svelte.js';

  let { item, account, onclose } = $props();

  let text = $state('');
  let warning = $state('');
  // Deliberately a one-time default, not a derived value: the composer is
  // mounted per reply, and the reader must stay in control of the field after
  // it is on screen. `untrack` says so rather than leaving it to be guessed.
  let visibility = $state(
    untrack(() => (item.core.visibility === 'private' ? 'private' : 'public')),
  );
  let sending = $state(false);
  let problem = $state(false);
  let done = $state(false);

  const who = $derived(
    plain(item.core.account?.display_name) || item.core.account?.username || item.core.account?.acct,
  );

  async function send(event) {
    event.preventDefault();
    if (!text.trim() || sending) return;
    sending = true;
    problem = false;
    try {
      await mastodon.reply(account, {
        inReplyToId: item.core.id,
        text: text.trim(),
        visibility,
        spoilerText: warning.trim(),
      });
      done = true;
      text = '';
      warning = '';
      setTimeout(() => onclose?.(), 1200);
    } catch {
      problem = true;
    } finally {
      sending = false;
    }
  }
</script>

<form class="composer" onsubmit={send}>
  <h3>{t('composer.replyTo', { name: who })}</h3>

  <p class="caveat">{t('composer.caveat')}</p>

  <label class="field">
    <span class="label">{t('composer.contentWarning')}</span>
    <input type="text" bind:value={warning} maxlength="180" />
  </label>

  <label class="field">
    <span class="visually-hidden">{t('composer.placeholder')}</span>
    <textarea
      bind:value={text}
      placeholder={t('composer.placeholder')}
      rows="4"
      maxlength="4000"
      required
    ></textarea>
  </label>

  <div class="row">
    <label class="field inline">
      <span class="label">{t('composer.visibility')}</span>
      <select bind:value={visibility}>
        <option value="public">{t('composer.visibilityPublic')}</option>
        <option value="unlisted">{t('composer.visibilityUnlisted')}</option>
        <option value="private">{t('composer.visibilityPrivate')}</option>
      </select>
    </label>

    <button type="button" class="ghost" onclick={() => onclose?.()}>{t('composer.cancel')}</button>
    <button type="submit" class="send" disabled={sending || !text.trim()}>
      {sending ? t('composer.sending') : t('composer.send')}
    </button>
  </div>

  {#if done}<p class="ok">{t('composer.sent')}</p>{/if}
  {#if problem}<p class="bad">{t('composer.error')}</p>{/if}
</form>

<style>
  .composer {
    display: grid;
    gap: 0.7rem;
    margin: 0.5rem 0 1.5rem;
    padding: 1rem 1.1rem;
    background: var(--ink-800);
    border: 1px solid var(--brass);
    border-radius: var(--radius);
  }

  h3 {
    margin: 0;
    font-size: var(--step-1);
  }

  .caveat {
    margin: 0;
    font-size: 0.85rem;
    color: var(--paper-dim);
    border-left: 2px solid var(--rule);
    padding-left: 0.7em;
  }

  .field {
    display: grid;
    gap: 0.25em;
  }

  .field.inline {
    display: flex;
    align-items: center;
    gap: 0.5em;
    margin-right: auto;
  }

  .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--paper-dim);
  }

  input,
  textarea,
  select {
    font: inherit;
    color: var(--paper);
    background: var(--ink-900);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 0.4em 0.6em;
  }

  textarea {
    font-family: var(--serif);
    resize: vertical;
    min-height: 5rem;
  }

  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6em;
  }

  .send {
    background: var(--brass);
    color: var(--ink-900);
    border: 1px solid var(--brass);
    border-radius: var(--radius);
    padding: 0.35em 1em;
    font-weight: 600;
  }

  .send:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .ghost {
    background: none;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 0.35em 0.9em;
    color: var(--paper-dim);
  }

  .ghost:hover {
    color: var(--paper);
  }

  .ok {
    margin: 0;
    color: var(--moss);
    font-size: 0.88rem;
  }

  .bad {
    margin: 0;
    color: var(--oxblood);
    font-size: 0.88rem;
  }
</style>
