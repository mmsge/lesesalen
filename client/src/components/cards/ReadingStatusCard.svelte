<script>
  /**
   * 5. Reading status — one line and a light.
   *
   * Four variants, three of them real events on a BookWyrm shelf:
   *
   *   vil-lesa  cold outline
   *   byrja     brass, lit
   *   ferdig    moss, lit
   *   utrekna   *derived from silence* — hatched, dashed, badged
   *
   * The fourth is the important one. **BookWyrm has no "stopped reading"
   * event**, so Lesesalen never says anybody gave up on a book. When a shelf
   * has been quiet for months we say exactly what we can see — nothing since
   * March — and label it as our own arithmetic, with a dashed "Rekna ut av
   * Lesesalen" badge. It never carries a page number: a page number would make
   * an inference look like a record (§Data contract, 5i).
   *
   * Every sentence is one whole catalogue string with slots, not fragments
   * glued together, because word order differs between nn and en.
   *
   * A status is one line: a light, the sentence, the age. It carries no byline
   * of its own — the person's name *is* the first word of the sentence, and it
   * is the thing that navigates to their page — and no action row, because a
   * generated shelf note is not something anyone replies to.
   */
  import Icon from '../Icon.svelte';
  import { t, tParts, formatAge, formatMonth } from '../../lib/i18n.svelte.js';
  import { plain } from '../../lib/sanitise.js';
  import { openable } from '../../lib/openable.js';

  let { item, onopen = null, onperson = null } = $props();

  const SENTENCES = {
    'vil-lesa': 'status.wantToRead',
    byrja: 'status.started',
    ferdig: 'status.finished',
    utrekna: 'status.stale',
  };

  const who = $derived(
    plain(item.core.account?.display_name) || item.core.account?.username || item.core.account?.acct || '',
  );
  const title = $derived(item.book?.tittel || t('cover.unknown'));
  const inferred = $derived(item.enrichment.status === 'utrekna');

  /**
   * `slutta` can still arrive from an instance that serves BookWyrm's
   * `stopped-reading` shelf, and `ukjend` is what a status whose prose we could
   * not read degrades to. Both get the neutral sentence: we know the shelf
   * moved, we do not know what the reader meant by it, and we will not guess.
   */
  const key = $derived(SENTENCES[item.enrichment.status] || 'status.updated');

  const parts = $derived(
    tParts(key, { who, title, since: formatMonth(item.core.created_at) }),
  );

  /** Where a tap on the card goes, for anyone who cannot see that it is a card. */
  const openLabel = $derived(
    t('card.open', {
      kind: t('kind.lesestatus'),
      who:
        plain(item.core.account?.display_name) ||
        item.core.account?.username ||
        item.core.account?.acct ||
        '',
    }),
  );
</script>

<!-- A derived line has no post behind it, so it is not a link and not a tab stop. -->
<article
  class="status enters"
  class:inferred
  use:openable={{ onopen: item.inferred ? null : () => onopen?.(item), label: openLabel }}
>
  <span class="light {item.enrichment.status || 'ukjend'}" aria-hidden="true"></span>

  <div class="body">
    <p class="sentence">
      {#each parts as part, index (index)}
        {#if part.slot === 'who' && onperson}
          <button
            type="button"
            class="who"
            aria-label={t('action.byPerson', { name: part.value })}
            onclick={(event) => {
              event.stopPropagation();
              onperson(item.core.account);
            }}
          >
            {part.value}
          </button>
        {:else if part.slot === 'title'}<span class="title">{part.value}</span>
        {:else if part.slot}{part.value}
        {:else}{part.text}{/if}
      {/each}
    </p>

    {#if inferred}
      <span class="badge">
        <Icon name="bang" size={12} stroke={1.3} />
        {t('status.inferredBy')}
      </span>
    {/if}
  </div>

  <time class="age" datetime={item.core.created_at}>{formatAge(item.core.created_at)}</time>
</article>

<style>
  .status {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 15px 20px;
    cursor: pointer;
  }

  /* Derived, and drawn so you can tell at a glance that it is derived. It is
     also not a link: there is no post behind it to open. */
  .status.inferred {
    cursor: default;
    padding: 14px 20px 18px;
    background: repeating-linear-gradient(
      135deg,
      rgba(23, 20, 15, 0) 0 9px,
      rgba(34, 29, 22, 0.5) 9px 18px
    );
  }

  .light {
    flex: none;
    margin-top: 6px;
    width: 8px;
    height: 8px;
    border-radius: 999px;
  }

  /* Wants to read: a cold outline — nothing has happened yet. */
  .light.vil-lesa {
    border: 1.5px solid var(--paper-dim);
  }

  /* Started: brass, and lit. */
  .light.byrja {
    background: var(--brass);
    box-shadow:
      0 0 0 4px rgba(201, 162, 39, 0.2),
      0 0 14px rgba(201, 162, 39, 0.7);
  }

  /* Finished: moss, and lit. The only place --moss appears. */
  .light.ferdig {
    background: var(--moss);
    box-shadow:
      0 0 0 4px rgba(74, 93, 66, 0.28),
      0 0 16px rgba(74, 93, 66, 0.7);
  }

  .light.slutta,
  .light.ukjend {
    border: 1.5px solid var(--rule);
    background: var(--panel-raised);
  }

  /* Derived: dashed, so it does not read as one of the three real lights. */
  .status.inferred .light {
    border: 1.5px dashed var(--paper-dim);
    background: none;
    box-shadow: none;
  }

  .body {
    flex: 1;
    min-width: 0;
  }

  .sentence {
    margin: 0;
    font-size: 0.95rem;
    color: var(--paper-dim);
  }

  .title {
    font-family: var(--serif);
    color: var(--paper-bright);
  }

  .status.inferred .title {
    color: var(--paper-prose);
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    padding: 3px 8px;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--paper-dim);
    border: 1px dashed var(--grey-dashed);
    border-radius: var(--radius-cover);
  }

  /* The name is the byline: it is where the person page is reached from.
     It sits inside a sentence, so the 44px target is made with padding that
     negative margin immediately takes back — the box grows, the words do not
     move, and unlike an invisible overlay the target is the element itself. */
  .who {
    display: inline-block;
    min-width: 44px;
    padding: 13px 10px;
    margin: -13px -10px;
    text-align: left;
    background: none;
    border: 0;
    font: inherit;
    line-height: 1.25;
    color: var(--paper);
    text-decoration: underline;
    text-decoration-color: var(--rule);
    text-underline-offset: 0.2em;
    vertical-align: baseline;
  }

  .age {
    flex: none;
    margin-top: 2px;
    font-size: 0.8rem;
    color: var(--paper-dim);
    white-space: nowrap;
  }
</style>
