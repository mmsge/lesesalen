<script>
  /**
   * A reply waiting for the network (5e).
   *
   * It shows **the reader's own words**, not "1 reply pending": what goes out
   * under somebody's name when the network returns is something they should be
   * able to read, change or throw away first.
   */
  import { dequeue, saveDraft } from '../lib/queue.svelte.js';
  import { t, formatNumber } from '../lib/i18n.svelte.js';

  let { drafts = [], onedit } = $props();

  function discard(draft) {
    dequeue(draft.id);
    saveDraft(draft.uri, null);
  }

  function edit(draft) {
    // Put it back in the composer exactly as it was, and stop it being sent
    // behind the reader's back in the meantime.
    saveDraft(draft.uri, { text: draft.text, warning: draft.warning, visibility: draft.visibility });
    dequeue(draft.id);
    onedit?.(draft);
  }
</script>

{#if drafts.length}
  <div class="queued">
    <p class="label dim">{t('queue.waiting', { n: formatNumber(drafts.length) })}</p>
    {#each drafts as draft (draft.id)}
      <p class="text">{t('queue.willSend', { text: `«${draft.text}»` })}</p>
      <div class="row">
        <button type="button" class="secondary" onclick={() => edit(draft)}>{t('queue.edit')}</button>
        <button type="button" class="secondary warn" onclick={() => discard(draft)}>
          {t('queue.discard')}
        </button>
      </div>
    {/each}
  </div>
{/if}

<style>
  .queued {
    width: min(100% - 40px, var(--column));
    margin: 0 auto 4px;
    padding: 14px 16px;
    background: var(--panel);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
  }

  .label {
    margin-bottom: 8px;
  }

  .text {
    margin: 0 0 12px;
    font-size: 0.95rem;
    color: var(--paper);
  }

  .row {
    display: flex;
    gap: 10px;
  }

  .row .secondary {
    flex: 1;
  }

  .warn {
    color: var(--warn);
  }
</style>
