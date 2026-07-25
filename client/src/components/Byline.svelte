<script>
  /**
   * Who wrote it, and when.
   *
   * The display name is rendered from the structured field as plain text, and
   * custom emoji come from the `emojis` array plus shortcodes — never from
   * injected markup. That is the rule for every remote field that has a
   * structured form: render from the structure, not from the HTML.
   */
  import { plain } from '../lib/sanitise.js';
  import { formatAge, t } from '../lib/i18n.svelte.js';
  import { handleOf } from '../lib/filters.js';

  let { account, createdAt, url = null, onperson = null } = $props();

  const name = $derived(plain(account?.display_name) || account?.username || account?.acct || '');
  const handle = $derived(handleOf(account));

  /** Split a display name into text and custom-emoji parts. */
  const parts = $derived.by(() => {
    const emojis = new Map((account?.emojis || []).map((emoji) => [emoji.shortcode, emoji.url]));
    if (!emojis.size) return [{ text: name }];
    return name.split(/:([a-zA-Z0-9_]+):/g).map((chunk, index) =>
      index % 2 === 1 && emojis.has(chunk)
        ? { emoji: emojis.get(chunk), code: chunk }
        : { text: chunk },
    );
  });

  const domain = $derived(handle.includes('@') ? handle.split('@').pop() : '');
</script>

<div class="byline">
  {#if onperson}
    <button type="button" class="who" onclick={() => onperson(account)} title={t('action.byPerson')}>
      {#each parts as part, index (index)}
        {#if part.emoji}
          <img class="emoji" src={part.emoji} alt={`:${part.code}:`} loading="lazy" />
        {:else}{part.text}{/if}
      {/each}
    </button>
  {:else}
    <span class="who">{name}</span>
  {/if}
  <span class="handle">{handle}</span>
  {#if url}
    <a class="when" href={url} rel="nofollow noopener noreferrer" target="_blank"
       title={domain ? t('card.openOriginal', { domain }) : ''}>
      <time datetime={createdAt}>{formatAge(createdAt)}</time>
    </a>
  {:else}
    <time class="when" datetime={createdAt}>{formatAge(createdAt)}</time>
  {/if}
</div>

<style>
  .byline {
    display: flex;
    align-items: baseline;
    gap: 0.5em;
    font-size: 0.88rem;
    color: var(--paper-dim);
    min-width: 0;
  }

  .who {
    background: none;
    border: 0;
    padding: 0;
    color: var(--paper);
    font: inherit;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 14rem;
  }

  button.who:hover {
    color: var(--brass);
  }

  .handle {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }

  .when {
    margin-left: auto;
    color: var(--paper-dim);
    text-decoration: none;
    white-space: nowrap;
  }

  .when:hover {
    color: var(--brass);
  }

  .emoji {
    height: 1.1em;
    width: auto;
    vertical-align: -0.15em;
  }
</style>
