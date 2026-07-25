<script>
  import { block, t } from '../lib/i18n.svelte.js';

  const sections = $derived(block('about.sections'));
</script>

<article class="page">
  <h1>{t('about.title')}</h1>
  {#each sections as section, index (index)}
    <section>
      <h2>{section.heading}</h2>
      {#each section.paragraphs as paragraph, line (line)}
        <p>{paragraph}</p>
      {/each}
    </section>
  {/each}
</article>

<style>
  .page {
    max-width: var(--measure);
    margin: 2rem 0 5rem;
  }

  h1 {
    font-size: var(--step-3);
    margin-bottom: 1.5rem;
  }

  section {
    margin-bottom: 2.5rem;
  }

  h2 {
    font-size: var(--step-1);
    color: var(--brass);
  }

  p {
    font-family: var(--serif);
    font-size: var(--step-1);
    line-height: 1.65;
    margin: 0 0 1em;
  }
</style>
