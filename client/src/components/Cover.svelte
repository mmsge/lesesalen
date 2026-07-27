<script>
  /**
   * A book cover. The loudest thing on the page, by design — and the component
   * everything else leans on.
   *
   * Four states, in this order (§Covers):
   *
   *   1. cover URL present  → use it
   *   2. resolving          → blank spine, a brass gleam sweeping across it
   *   3. no cover, has book → synthesised jacket: gutter + title + rule + author
   *   4. no book at all     → dashed outline, book glyph, "Ukjend bok"
   *
   * The jacket's cloth and the spine's silhouette are pure functions of the
   * BookWyrm work id (lib/spine.js), so a book looks identical across sessions,
   * shelves and devices. Never seed them from load order or a random number.
   *
   * Covers are always served from our own origin: readers never hit BookWyrm
   * instances for images, so no reader IP leaks outward.
   *
   * A long press (420 ms) or a right-click opens the book sheet. The press is
   * swallowed on the way out so it does not also open the post underneath.
   */
  import Icon from './Icon.svelte';
  import { averageColour } from '../lib/colour.js';
  import { jacketOf, coverShadow } from '../lib/spine.js';
  import { t } from '../lib/i18n.svelte.js';

  let { book = null, width = 132, tilt = false, onbook = null } = $props();

  const HOLD_MS = 420;

  let loaded = $state(false);
  let held = $state(false);
  let timer = null;

  const title = $derived(book?.tittel || t('cover.unknown'));
  const author = $derived((book?.forfattarar || [])[0] || null);
  // A draft book has come off the cover attachment's name and its edition is
  // still being fetched, so a cover may yet arrive: show the gleam rather than
  // a jacket we would have to replace a second later (ADR 0010).
  const state = $derived(
    !book ? 'unknown' : book.omslag ? 'image' : book.utkast ? 'resolving' : 'jacket',
  );
  // No work id yet means no work id to hash; the title is the only stable thing
  // a draft has, and it keeps the jacket steady until the edition lands.
  const seed = $derived(book?.id || book?.tittel || '');
  const jacket = $derived(jacketOf(seed, width));
  const tint = $derived(book?.blurhash ? averageColour(book.blurhash) : null);
  const holdable = $derived(Boolean(onbook && book));

  /**
   * One accessible name for the whole cover, carried by the wrapper.
   *
   * The wrapper is either a button (its label wins) or `role="img"` (its
   * contents are ignored), so the state has to be said here or not at all —
   * hence "slår opp omslaget" rather than a visually-hidden span nobody reaches.
   */
  const spoken = $derived.by(() => {
    if (state === 'resolving') return t('cover.lookingUp', { title });
    if (state === 'jacket') return t('cover.synthesised', { title });
    if (state === 'unknown') return t('cover.unknown');
    return t('cover.alt', { title });
  });

  function start() {
    if (!holdable) return;
    clearTimeout(timer);
    timer = setTimeout(() => {
      held = true;
      onbook?.(book);
    }, HOLD_MS);
  }

  function stop() {
    clearTimeout(timer);
  }

  /** A long press must not also count as a tap on the card underneath. */
  function onclick(event) {
    if (!holdable) return;
    event.stopPropagation();
    if (held) {
      held = false;
      return;
    }
    onbook?.(book);
  }

  function oncontextmenu(event) {
    if (!holdable) return;
    event.preventDefault();
    event.stopPropagation();
    onbook?.(book);
  }
</script>

<svelte:element
  this={holdable ? 'button' : 'div'}
  type={holdable ? 'button' : undefined}
  class="cover {state}"
  class:tilt
  role={holdable ? undefined : 'img'}
  aria-label={holdable ? t('cover.holdFor', { title: spoken }) : spoken}
  style:width={`${width}px`}
  style:box-shadow={state === 'unknown' ? 'none' : coverShadow(width)}
  style:background={state === 'image'
    ? tint || 'var(--panel-raised)'
    : state === 'jacket'
      ? jacket.gradient
      : 'var(--panel-raised)'}
  onpointerdown={start}
  onpointerup={stop}
  onpointerleave={stop}
  onpointercancel={stop}
  {onclick}
  {oncontextmenu}
>
  {#if state === 'image'}
    <img
      src={book.omslag}
      alt=""
      loading="lazy"
      decoding="async"
      class:loaded
      onload={() => (loaded = true)}
    />
  {:else if state === 'resolving'}
    <span class="gleam" aria-hidden="true"></span>
  {:else if state === 'jacket'}
    <span class="gutter" aria-hidden="true" style:width={`${jacket.gutter}px`}></span>
    {#if jacket.lettered}
      <span
        class="type"
        aria-hidden="true"
        style:left={`${jacket.gutter + 11}px`}
        style:top={`${jacket.top}px`}
      >
        <span class="jacket-title" style:font-size={`${jacket.titleSize}rem`}>{title}</span>
        <span class="jacket-rule"></span>
        <!-- No author line at all when there is no author: no "ukjend", no dash. -->
        {#if author}<span class="jacket-author">{author}</span>{/if}
      </span>
    {/if}
    <span class="sheen" aria-hidden="true"></span>
  {:else}
    <span class="unknown-mark">
      <Icon name="book" size={24} stroke={1.4} />
      <span class="unknown-label">{t('cover.unknown')}</span>
    </span>
  {/if}
</svelte:element>

<style>
  .cover {
    position: relative;
    flex: none;
    display: block;
    aspect-ratio: 2 / 3;
    border: 0;
    border-radius: var(--radius-cover);
    overflow: hidden;
    padding: 0;
    touch-action: manipulation;
    /* A held cover must not also select the title behind it. */
    -webkit-user-select: none;
    user-select: none;
  }

  .cover.unknown {
    border: 1px dashed var(--grey-dashed);
    background: var(--panel-raised);
  }

  .cover.tilt {
    transform: rotate(-1.5deg);
  }

  img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0;
  }

  img.loaded {
    opacity: 1;
  }

  @media (prefers-reduced-motion: no-preference) {
    img {
      transition: opacity 240ms ease-out;
    }
  }

  /* 2. Resolving: a brass gleam sweeping across an empty spine. Static under
     prefers-reduced-motion, where the cover's own label carries the state. */
  .gleam {
    position: absolute;
    inset: 0;
    background: linear-gradient(100deg, transparent 30%, rgba(201, 162, 39, 0.16) 50%, transparent 70%);
    animation: lampSweep 1.4s ease-in-out infinite;
  }

  /* 3. The synthesised jacket. */
  .gutter {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    background: linear-gradient(90deg, rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.05));
    border-right: 1px solid rgba(201, 162, 39, 0.28);
  }

  .type {
    position: absolute;
    right: 12px;
    display: grid;
    gap: 6px;
    text-align: left;
  }

  .jacket-title {
    font-family: var(--serif);
    line-height: 1.22;
    color: var(--paper-bright);
  }

  .jacket-rule {
    width: 24px;
    height: 1px;
    background: rgba(246, 239, 225, 0.55);
  }

  .jacket-author {
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: rgba(246, 239, 225, 0.78);
  }

  /* Lit from the top left, like everything else in the room. */
  .sheen {
    position: absolute;
    inset: 0;
    background: linear-gradient(205deg, rgba(255, 235, 180, 0.2), transparent 45%);
  }

  /* 4. No book at all. */
  .unknown-mark {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    align-content: center;
    gap: 6px;
    padding: 6px;
    text-align: center;
    color: var(--paper-dim);
  }

  .unknown-label {
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    line-height: 1.3;
  }
</style>
