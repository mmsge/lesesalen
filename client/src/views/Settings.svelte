<script>
  /**
   * Settings (4h) — its own route, not a modal.
   *
   * Five blocks: the account, the language, the collection **with its size** so
   * that "Tøm samlinga" is an informed action rather than a leap, the two
   * reading preferences, and log out.
   *
   * The ephemeral-session switch is not in the design but stays here: it is the
   * control that keeps a shared machine from accumulating an on-disk archive of
   * other people's reading, and removing it would quietly undo ADR 0009.
   */
  import Icon from '../components/Icon.svelte';
  import * as auth from '../lib/auth.js';
  import * as kista from '../lib/kista.js';
  import { forget } from '../lib/collection.svelte.js';
  import { isEphemeral, setEphemeral } from '../lib/storage.js';
  import { prefs, setCwOpen, setPercent } from '../lib/prefs.svelte.js';
  import { show } from '../lib/toast.svelte.js';
  import { link } from '../lib/router.svelte.js';
  import { i18n, setLanguage, t, formatNumber } from '../lib/i18n.svelte.js';

  let { account, onlogout } = $props();

  let ephemeral = $state(isEphemeral());
  let leaving = $state(false);
  let stored = $state({ posts: 0, books: 0, bytes: null });

  $effect(() => {
    kista.size().then((found) => (stored = found));
  });

  const size = $derived(
    stored.bytes === null
      ? null
      : `${formatNumber(Math.round((stored.bytes / 1048576) * 10) / 10)} MB`,
  );

  async function logOut() {
    leaving = true;
    await auth.logOut();
    onlogout?.();
    leaving = false;
  }

  /**
   * Ticking "log me out when I close the tab" must also remove the collection
   * already on disk — otherwise the setting protects the token and leaves an
   * archive of other people's reading on a shared machine (ADR 0009).
   */
  async function onEphemeralChange() {
    ephemeral = !ephemeral;
    setEphemeral(ephemeral);
    if (ephemeral) await kista.destroy();
    stored = await kista.size();
  }

  async function clearCollection() {
    await forget();
    stored = await kista.size();
    show('settings.collectionCleared');
  }
</script>

<div class="settings fades">
  <header><h1>{t('settings.heading')}</h1></header>

  {#if account}
    <section>
      <p class="label dim">{t('settings.account')}</p>
      <div class="panel row">
        <span class="avatar" aria-hidden="true">{account.domain.slice(0, 1).toUpperCase()}</span>
        <span class="stack">
          <span class="strong">{t('settings.loggedInAs', { domain: account.domain })}</span>
          <span class="quiet">{t('settings.tokenHere')}</span>
        </span>
      </div>
    </section>
  {/if}

  <section>
    <p class="label dim">{t('settings.language')}</p>
    <div class="pair">
      <button type="button" class:on={i18n.lang === 'nn'} onclick={() => setLanguage('nn')}>
        {t('settings.languageNn')}
      </button>
      <button type="button" class:on={i18n.lang === 'en'} onclick={() => setLanguage('en')}>
        {t('settings.languageEn')}
      </button>
    </div>
  </section>

  <section>
    <p class="label dim">{t('settings.collection')}</p>
    <div class="list">
      <div class="row">
        <span class="strong">
          {t('settings.collectionSize', {
            posts: formatNumber(stored.posts),
            books: formatNumber(stored.books),
          })}
        </span>
        {#if size}<span class="quiet">{size}</span>{/if}
      </div>
      <button type="button" class="row" onclick={clearCollection}>
        <span class="strong">{t('settings.clearCollection')}</span>
        <span class="quiet">{t('settings.clearCollectionNote')}</span>
      </button>
    </div>
    <p class="help">{t('settings.collectionHelp')}</p>
  </section>

  <section>
    <p class="label dim">{t('settings.reading')}</p>
    <div class="list">
      <div class="row">
        <span class="strong">{t('settings.cwOpen')}</span>
        <button
          type="button"
          role="switch"
          class="switch"
          class:on={prefs.cwOpen}
          aria-checked={prefs.cwOpen}
          aria-label={t('settings.cwOpen')}
          onclick={() => setCwOpen(!prefs.cwOpen)}
        >
          <span class="track"><span class="knob"></span></span>
        </button>
      </div>
      <div class="row">
        <span class="strong">{t('settings.percent')}</span>
        <button
          type="button"
          role="switch"
          class="switch"
          class:on={prefs.percent}
          aria-checked={prefs.percent}
          aria-label={t('settings.percent')}
          onclick={() => setPercent(!prefs.percent)}
        >
          <span class="track"><span class="knob"></span></span>
        </button>
      </div>
      {#if account}
        <div class="row">
          <span class="stack">
            <span class="strong">{t('settings.ephemeral')}</span>
            <span class="quiet">{t('settings.ephemeralHelp')}</span>
          </span>
          <button
            type="button"
            role="switch"
            class="switch"
            class:on={ephemeral}
            aria-checked={ephemeral}
            aria-label={t('settings.ephemeral')}
            onclick={onEphemeralChange}
          >
            <span class="track"><span class="knob"></span></span>
          </button>
        </div>
      {/if}
    </div>
  </section>

  {#if account}
    <section>
      <button type="button" class="out" onclick={logOut} disabled={leaving}>
        {leaving ? t('settings.loggingOut') : t('settings.logOut')}
      </button>
      <p class="help">{t('settings.logOutHelp')}</p>
    </section>
  {:else}
    <section>
      <a class="primary" href="/logg-inn" use:link>{t('landing.cta')}</a>
    </section>
  {/if}

  <nav class="links">
    <a href="/om" use:link>{t('nav.about')}</a>
    <a href="/personvern" use:link>{t('nav.privacy')}</a>
    <a href="https://github.com/mmsge/lesesalen" rel="noopener noreferrer" target="_blank">
      {t('nav.source')}
      <Icon name="external" size={14} />
    </a>
  </nav>
</div>

<style>
  .settings {
    padding-bottom: calc(var(--tabbar) + var(--safe-bottom));
  }

  header,
  section,
  .links {
    width: min(100%, var(--column));
    margin-inline: auto;
    padding-inline: 20px;
  }

  header {
    padding-top: calc(18px + var(--safe-top));
    padding-bottom: 14px;
    background: radial-gradient(80% 130% at 50% -20%, rgba(201, 162, 39, 0.18), rgba(15, 13, 11, 0) 70%);
  }

  h1 {
    margin: 0;
    font-size: 1.3rem;
    color: var(--paper-bright);
  }

  section {
    margin-bottom: 18px;
  }

  .label {
    margin-bottom: 10px;
  }

  .panel {
    background: var(--panel);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 12px 14px;
  }

  /* Hairline-separated rows, all at least 52px. */
  .list {
    display: grid;
    gap: 1px;
    background: var(--rule);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    overflow: hidden;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 52px;
    padding: 10px 14px;
    background: var(--panel);
    border: 0;
    text-align: left;
    width: 100%;
  }

  .strong {
    flex: 1;
    min-width: 0;
    font-size: 0.92rem;
    color: var(--paper);
  }

  .stack {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 2px;
  }

  .stack .strong {
    flex: none;
  }

  .quiet {
    flex: none;
    font-size: 0.82rem;
    color: var(--paper-dim);
  }

  .stack .quiet {
    flex: none;
  }

  .avatar {
    flex: none;
    width: 36px;
    height: 36px;
    border-radius: 999px;
    background: var(--rule);
    display: grid;
    place-items: center;
    font-family: var(--serif);
    color: var(--brass);
  }

  .pair {
    display: flex;
    gap: 8px;
  }

  .pair button {
    flex: 1;
    min-height: 48px;
    background: none;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    color: var(--paper-dim);
    font-size: 0.95rem;
  }

  .pair button.on {
    background: var(--brass);
    border-color: var(--brass);
    color: var(--ink);
    font-weight: 600;
  }

  /* The track is 44×26 because that is what a switch looks like; the control
     around it is 44×44 because that is what a thumb needs. */
  .switch {
    flex: none;
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    padding: 0;
    border: 0;
    background: none;
  }

  .track {
    position: relative;
    display: block;
    width: 44px;
    height: 26px;
    border-radius: 999px;
    background: var(--rule);
  }

  .switch.on .track {
    background: var(--brass);
  }

  .knob {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 20px;
    height: 20px;
    border-radius: 999px;
    background: var(--paper-dim);
  }

  .switch.on .knob {
    left: 21px;
    background: var(--ink);
  }

  @media (prefers-reduced-motion: no-preference) {
    .knob {
      transition: left 0.18s ease;
    }
  }

  .out {
    width: 100%;
    min-height: 48px;
    background: none;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    color: var(--warn);
    font-size: 0.95rem;
  }

  .out:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .help {
    margin: 12px 0 0;
    font-size: 0.82rem;
    color: var(--paper-dim);
  }

  .links {
    display: flex;
    gap: 8px;
    margin-top: 14px;
    padding-bottom: 20px;
  }

  .links a {
    flex: 1;
    min-height: 44px;
    display: grid;
    grid-auto-flow: column;
    place-items: center;
    gap: 6px;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    font-size: 0.85rem;
    text-decoration: none;
    color: var(--brass);
  }

  section .primary {
    text-decoration: none;
  }
</style>
