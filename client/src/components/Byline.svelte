<script>
  /**
   * Who wrote it, and when — "Åsta · 3 t sidan".
   *
   * Tapping it goes to that person's own page (`/@handle@host`), not to a
   * person filter on the feed: the page is a real address that can be shared,
   * and it is the only thing here that works without a session.
   *
   * The display name is rendered from the structured field as plain text, and
   * custom emoji come from the `emojis` array plus shortcodes — never from
   * injected markup. That is the rule for every remote field that has a
   * structured form: render from the structure, not from the HTML.
   */
  import { plain } from '../lib/sanitise.js';
  import { formatAge, t } from '../lib/i18n.svelte.js';
  import { handleOf } from '../lib/filters.js';

  let { account, createdAt, onperson = null } = $props();

  const name = $derived(plain(account?.display_name) || account?.username || account?.acct || '');
  const handle = $derived(handleOf(account));

  /** Split a display name into text and custom-emoji parts. */
  const parts = $derived.by(() => {
    const emojis = new Map((account?.emojis || []).map((emoji) => [emoji.shortcode, emoji.url]));
    if (!emojis.size) return [{ text: name }];
    return name
      .split(/:([a-zA-Z0-9_]+):/g)
      .map((chunk, index) =>
        index % 2 === 1 && emojis.has(chunk) ? { emoji: emojis.get(chunk), code: chunk } : { text: chunk },
      );
  });
</script>

{#if onperson}
  <button
    type="button"
    class="byline"
    aria-label={t('action.byPerson', { name: name || handle })}
    onclick={(event) => {
      event.stopPropagation();
      onperson(account);
    }}
  >
    <span class="who">
      {#each parts as part, index (index)}
        {#if part.emoji}
          <img class="emoji" src={part.emoji} alt={`:${part.code}:`} loading="lazy" />
        {:else}{part.text}{/if}
      {/each}
    </span>
    <span aria-hidden="true">·</span>
    <time datetime={createdAt}>{t('card.ago', { age: formatAge(createdAt) })}</time>
  </button>
{:else}
  <span class="byline">
    <span class="who">{name}</span>
    <span aria-hidden="true">·</span>
    <time datetime={createdAt}>{t('card.ago', { age: formatAge(createdAt) })}</time>
  </span>
{/if}

<style>
  .byline {
    display: inline-flex;
    align-items: baseline;
    gap: 0.35em;
    min-width: 0;
    max-width: 100%;
    padding: 0;
    background: none;
    border: 0;
    font: inherit;
    font-size: 0.8rem;
    color: var(--paper-dim);
    text-align: left;
  }

  button.byline {
    /* The row it sits in is 44px tall; the text itself is the label. */
    min-height: 44px;
    align-items: center;
    text-decoration: underline;
    text-decoration-color: var(--rule);
    text-underline-offset: 0.2em;
  }

  button.byline:hover {
    color: var(--paper);
  }

  .who {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 12rem;
  }

  time {
    white-space: nowrap;
  }

  .emoji {
    height: 1.1em;
    width: auto;
    vertical-align: -0.15em;
  }
</style>
