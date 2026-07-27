<script>
  /**
   * The shape of a review, while the first shelf is still on its way (4b).
   *
   * A skeleton stands in for a card that has not arrived at all. It is never
   * used for a card that has arrived incomplete: posts come in whole, and a
   * half-drawn post would teach the reader to distrust the ones that are real.
   */
  import { t } from '../lib/i18n.svelte.js';
</script>

<div class="skeleton" aria-hidden="true">
  <p class="label">{t('kind.omtale')}</p>
  <div class="head">
    <span class="cover"><span class="gleam"></span></span>
    <div class="lines">
      <span class="line tall"></span>
      <span class="line tall short"></span>
      <span class="line thin"></span>
    </div>
  </div>
  <div class="body">
    <span class="line"></span>
    <span class="line"></span>
    <span class="line short"></span>
  </div>
</div>

<style>
  .skeleton {
    width: min(100%, var(--column));
    margin-inline: auto;
    padding: 20px 20px 16px;
  }

  .label {
    margin-bottom: 12px;
  }

  .head {
    display: flex;
    gap: 18px;
    align-items: flex-end;
  }

  .cover {
    position: relative;
    flex: none;
    width: 132px;
    aspect-ratio: 2 / 3;
    border-radius: var(--radius-cover);
    background: var(--panel-raised);
    border: 1px solid var(--rule);
    overflow: hidden;
  }

  .gleam {
    position: absolute;
    inset: 0;
    background: linear-gradient(100deg, transparent 30%, rgba(201, 162, 39, 0.16) 50%, transparent 70%);
    animation: lampSweep 1.4s ease-in-out infinite;
  }

  .lines {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 9px;
    padding-bottom: 4px;
  }

  .body {
    display: grid;
    gap: 8px;
    margin-top: 14px;
  }

  .line {
    height: 12px;
    border-radius: var(--radius-cover);
    background: var(--panel-raised);
  }

  .line.tall {
    height: 18px;
  }

  .line.thin {
    height: 11px;
    width: 52%;
    background: #1c1811;
  }

  .line.short {
    width: 64%;
    background: #1c1811;
  }
</style>
