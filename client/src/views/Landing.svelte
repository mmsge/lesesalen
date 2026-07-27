<script>
  /**
   * What a logged-out visitor sees (3d): a shelf, not an empty feed.
   *
   * Hero, the two privacy principles, and **one invented quotation card** —
   * enough to show what the treatment looks like without revealing what anybody
   * reads. There is no logged-out feed and no discovery surface, and that is the
   * point rather than an omission (ADR 0008).
   */
  import Card from '../components/Card.svelte';
  import ShelfStrip from '../components/ShelfStrip.svelte';
  import { SAMPLES } from '../lib/samples.js';
  import { t } from '../lib/i18n.svelte.js';
  import { link } from '../lib/router.svelte.js';

  // The books the invented samples are about, so the shelf is the same shelf.
  const books = $derived([...new Map(SAMPLES.map((item) => [item.book.id, item.book])).values()]);
  const showcase = $derived(SAMPLES.find((item) => item.enrichment.slag === 'sitat'));
</script>

<div class="landing">
  <section class="hero">
    <p class="label">{t('app.name')}</p>
    <h1>{t('landing.heading')}</h1>
    <p class="lead">{t('landing.lead')}</p>
    <a class="primary" href="/logg-inn" use:link>{t('landing.cta')}</a>
  </section>

  <ShelfStrip {books} />

  <section class="principles">
    <div class="principle">
      <h2>{t('landing.principleHeading')}</h2>
      <p>{t('landing.principle')}</p>
    </div>
    <div class="principle">
      <h2>{t('landing.noCrawlerHeading')}</h2>
      <p>{t('landing.noCrawler')}</p>
    </div>

    <p class="label dim">{t('landing.sampleHeading')}</p>
    <p class="note">{t('landing.sampleNote')}</p>
  </section>

  {#if showcase}
    <Card item={showcase} />
  {/if}

  <div class="rail dim"></div>

  <nav class="links">
    <a href="/om" use:link>{t('nav.about')}</a>
    <a href="/personvern" use:link>{t('nav.privacy')}</a>
  </nav>
</div>

<style>
  .landing {
    padding-bottom: calc(var(--tabbar) + var(--safe-bottom));
  }

  .hero,
  .principles,
  .links {
    width: min(100%, var(--column));
    margin-inline: auto;
    padding-inline: 22px;
  }

  .hero {
    padding-top: calc(30px + var(--safe-top));
    padding-bottom: 24px;
    background: radial-gradient(80% 130% at 50% -20%, rgba(201, 162, 39, 0.24), transparent 70%);
  }

  h1 {
    font-size: 2.1rem;
    line-height: 1.14;
    margin: 12px 0;
    color: var(--paper-bright);
  }

  .lead {
    font-family: var(--serif);
    font-size: 1.1rem;
    line-height: 1.55;
    color: var(--paper-prose);
    margin: 0 0 22px;
  }

  .hero .primary {
    text-decoration: none;
  }

  .principles {
    padding-top: 24px;
    padding-bottom: 8px;
  }

  .principle {
    margin-bottom: 22px;
  }

  .principle h2 {
    font-size: 1.15rem;
    margin: 0 0 6px;
    color: var(--brass);
  }

  .principle p {
    margin: 0;
    color: var(--paper-dim);
  }

  .label {
    margin-bottom: 6px;
  }

  .note {
    margin: 0 0 14px;
    font-size: 0.88rem;
    color: var(--paper-dim);
  }

  .links {
    display: flex;
    gap: 8px;
    padding-top: 20px;
    padding-bottom: 24px;
  }

  .links a {
    flex: 1;
    min-height: 44px;
    display: grid;
    place-items: center;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    font-size: 0.85rem;
    text-decoration: none;
  }
</style>
