<script>
  /**
   * "På hylla no" — a row of book spines standing on a lit rail.
   *
   * Width and height come off the work id (lib/spine.js), so the skyline is the
   * same every time you open the app and a book you recognise stays
   * recognisable. A spine that is still being looked up stands blank; an empty
   * shelf stands as dashed outlines on an unlit rail (4a).
   *
   * Target size: a spine is 22–55 px wide because that is what makes a shelf
   * read as a shelf, so the hit area is widened into the gap around it rather
   * than the spine being fattened to 44 px. Every book here is also reachable
   * through a full-size cover in the feed and through the book row in the post
   * detail, both of which clear 44 px comfortably.
   */
  import { spineOf } from '../lib/spine.js';
  import { t } from '../lib/i18n.svelte.js';

  let { books = [], empty = 0, dim = false, onbook = null, label = null } = $props();

  const spines = $derived(
    books.map((book) => ({ book, ...spineOf(book?.id || book?.tittel || '') })),
  );
  // Empty shelves still need a skyline, and it has to be a stable one.
  const ghosts = $derived(
    Array.from({ length: empty }, (_, index) => spineOf(`tom-${index}`)),
  );
</script>

<div class="strip" class:dim>
  {#if label}<p class="label dim heading">{label}</p>{/if}

  <div class="rack">
    <div class="spines">
      {#each spines as spine (spine.book?.id || spine.book?.tittel)}
        {#if onbook && spine.book}
          <button
            type="button"
            class="spine"
            style:width={`${spine.width}px`}
            style:height={`${spine.height}px`}
            style:background={spine.book.utkast && !spine.book.omslag ? 'var(--panel-raised)' : spine.gradient}
            aria-label={t('cover.holdFor', { title: spine.book.tittel || t('cover.unknown') })}
            onclick={() => onbook(spine.book)}
          >
            <span class="gutter" aria-hidden="true"></span>
          </button>
        {:else}
          <span
            class="spine"
            style:width={`${spine.width}px`}
            style:height={`${spine.height}px`}
            style:background={spine.gradient}
          >
            <span class="gutter" aria-hidden="true"></span>
          </span>
        {/if}
      {/each}

      {#each ghosts as ghost, index (index)}
        <span
          class="spine ghost"
          aria-hidden="true"
          style:width={`${ghost.width}px`}
          style:height={`${ghost.height}px`}
        ></span>
      {/each}
    </div>

    <div class="rail" class:dim></div>
  </div>
</div>

<style>
  .heading {
    padding: 0 20px;
    margin-bottom: 10px;
  }

  .rack {
    /* The rail runs the full width of the screen; the spines are inset with
       the rest of the content. */
    margin: 0;
  }

  .spines {
    display: flex;
    align-items: flex-end;
    gap: 9px;
    height: 100px;
    padding: 0 20px;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .spines::-webkit-scrollbar {
    display: none;
  }

  .strip.dim .spines {
    opacity: 0.4;
  }

  .spine {
    position: relative;
    flex: none;
    display: block;
    border: 0;
    padding: 0;
    border-radius: var(--radius-cover);
    box-shadow:
      0 12px 18px rgba(0, 0, 0, 0.7),
      0 1px 0 rgba(246, 239, 225, 0.12) inset;
  }

  /* The hit area reaches into the gap on both sides without ever overlapping a
     neighbour's, so a tap is never ambiguous. */
  button.spine::after {
    content: '';
    position: absolute;
    inset: 0 -4.5px;
  }

  .spine.ghost {
    background: rgba(23, 20, 15, 0.5);
    border: 1px dashed var(--rule);
    box-shadow: none;
  }

  .gutter {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    width: 5px;
    background: rgba(0, 0, 0, 0.5);
    border-right: 1px solid rgba(201, 162, 39, 0.25);
  }
</style>
