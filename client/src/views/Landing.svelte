<script>
  /**
   * What a logged-out visitor sees: an explainer and some invented sample cards.
   *
   * Never other people's reading. There is no logged-out feed and no discovery
   * surface, and that is the point rather than an omission.
   */
  import Card from '../components/Card.svelte';
  import { SAMPLES } from '../lib/samples.js';
  import { t } from '../lib/i18n.svelte.js';
  import { link } from '../lib/router.svelte.js';
</script>

<section class="hero">
  <h1>{t('landing.heading')}</h1>
  <p class="lead">{t('landing.lead')}</p>
  <a class="cta" href="/innstillingar" use:link>{t('landing.cta')}</a>
</section>

<section class="principles">
  <div class="principle">
    <h2>{t('landing.principleHeading')}</h2>
    <p>{t('landing.principle')}</p>
  </div>
  <div class="principle">
    <h2>{t('landing.noCrawlerHeading')}</h2>
    <p>{t('landing.noCrawler')}</p>
  </div>
</section>

<section class="samples">
  <h2>{t('landing.sampleHeading')}</h2>
  <p class="note">{t('landing.sampleNote')}</p>
  <div class="column">
    {#each SAMPLES as item (item.id)}
      <Card {item} />
    {/each}
  </div>
</section>

<style>
  .hero {
    padding: 3rem 0 2.5rem;
    border-bottom: 1px solid var(--rule);
  }

  h1 {
    font-size: var(--step-4);
    margin: 0 0 0.4em;
  }

  .lead {
    font-family: var(--serif);
    font-size: var(--step-1);
    line-height: 1.6;
    max-width: var(--measure);
    color: var(--paper);
    margin: 0 0 1.5em;
  }

  .cta {
    display: inline-block;
    background: var(--brass);
    color: var(--ink-900);
    font-weight: 600;
    text-decoration: none;
    padding: 0.5em 1.3em;
    border-radius: var(--radius);
  }

  .cta:hover {
    background: var(--paper);
    color: var(--ink-900);
  }

  .principles {
    display: grid;
    gap: 2rem;
    padding: 2.5rem 0;
    border-bottom: 1px solid var(--rule);
  }

  @media (min-width: 40rem) {
    .principles {
      grid-template-columns: 1fr 1fr;
    }
  }

  .principle h2 {
    font-size: var(--step-1);
    color: var(--brass);
  }

  .principle p {
    margin: 0;
    color: var(--paper-dim);
    max-width: var(--measure);
  }

  .samples {
    padding: 2.5rem 0 4rem;
  }

  .samples h2 {
    font-size: var(--step-2);
  }

  .note {
    color: var(--paper-dim);
    font-size: 0.9rem;
    margin: 0 0 2rem;
  }

  .column {
    display: grid;
    gap: 1.5rem;
  }
</style>
