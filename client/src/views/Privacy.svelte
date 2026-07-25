<script>
  import { block, t, formatDate } from '../lib/i18n.svelte.js';

  const points = $derived(block('privacy.points'));
  const kept = $derived(block('privacy.kept'));

  // The page's own modified date, taken from the metadata the server stamped
  // into the head from git history — not from the clock.
  const modified = $derived(
    document.querySelector('meta[name="last-modified"]')?.getAttribute('content') || null,
  );
</script>

<article class="page">
  <h1>{t('privacy.title')}</h1>
  <p class="lead">{t('privacy.lead')}</p>

  <dl>
    {#each points as point, index (index)}
      <div class="point">
        <dt>{point.term}</dt>
        <dd>{point.detail}</dd>
      </div>
    {/each}
  </dl>

  <section>
    <h2>{t('privacy.keptHeading')}</h2>
    {#each kept as paragraph, index (index)}
      <p>{paragraph}</p>
    {/each}
  </section>

  <section class="caveat">
    <h2>{t('privacy.caveatHeading')}</h2>
    <p>{t('privacy.caveat')}</p>
  </section>

  <section>
    <h2>{t('privacy.rightsHeading')}</h2>
    <p>{t('privacy.rights')}</p>
  </section>

  {#if modified}
    <p class="updated">{t('privacy.updated', { date: formatDate(modified) })}</p>
  {/if}
</article>

<style>
  .page {
    max-width: var(--measure);
    margin: 2rem 0 5rem;
  }

  h1 {
    font-size: var(--step-3);
    margin-bottom: 0.3em;
  }

  .lead {
    color: var(--paper-dim);
    margin: 0 0 2rem;
  }

  dl {
    margin: 0 0 2.5rem;
    display: grid;
    gap: 1.1rem;
  }

  dt {
    font-family: var(--serif);
    font-size: var(--step-1);
    color: var(--brass);
  }

  dd {
    margin: 0.2em 0 0;
    color: var(--paper);
  }

  section {
    margin-bottom: 2.5rem;
  }

  h2 {
    font-size: var(--step-1);
  }

  p {
    font-family: var(--serif);
    line-height: 1.65;
    margin: 0 0 1em;
  }

  .caveat {
    border-left: 2px solid var(--oxblood);
    padding-left: 1.2em;
  }

  .updated {
    font-family: var(--sans);
    font-size: 0.85rem;
    color: var(--paper-dim);
  }
</style>
