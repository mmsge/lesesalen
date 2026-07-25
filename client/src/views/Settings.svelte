<script>
  import Login from './Login.svelte';
  import * as auth from '../lib/auth.js';
  import * as kista from '../lib/kista.js';
  import { forget } from '../lib/collection.svelte.js';
  import { isEphemeral, setEphemeral } from '../lib/storage.js';
  import { i18n, setLanguage, t } from '../lib/i18n.svelte.js';

  let { account, onlogout } = $props();

  let ephemeral = $state(isEphemeral());
  let leaving = $state(false);
  let clearing = $state(false);
  let cleared = $state(false);

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
    setEphemeral(ephemeral);
    if (ephemeral) await kista.destroy();
  }

  async function clearCollection() {
    clearing = true;
    cleared = false;
    await forget();
    clearing = false;
    cleared = true;
  }
</script>

<h1>{t('settings.heading')}</h1>

<section>
  <h2>{t('settings.language')}</h2>
  <div class="choices">
    <button type="button" class:on={i18n.lang === 'nn'} onclick={() => setLanguage('nn')}>
      {t('settings.languageNn')}
    </button>
    <button type="button" class:on={i18n.lang === 'en'} onclick={() => setLanguage('en')}>
      {t('settings.languageEn')}
    </button>
  </div>
</section>

<section>
  <h2>{t('settings.account')}</h2>
  {#if account}
    <p class="where">{t('settings.loggedInAs', { domain: account.domain })}</p>

    <label class="toggle">
      <input type="checkbox" bind:checked={ephemeral} onchange={onEphemeralChange} />
      <span>
        {t('settings.ephemeral')}
        <span class="help">{t('settings.ephemeralHelp')}</span>
      </span>
    </label>

    <button type="button" class="out" onclick={logOut} disabled={leaving}>
      {leaving ? t('settings.loggingOut') : t('settings.logOut')}
    </button>
    <p class="help">{t('settings.logOutHelp')}</p>
  {:else}
    <Login />
  {/if}
</section>

{#if account}
  <section>
    <h2>{t('settings.collection')}</h2>
    <p class="help">{t('settings.collectionHelp')}</p>
    <button type="button" class="out" onclick={clearCollection} disabled={clearing}>
      {clearing ? t('settings.clearingCollection') : t('settings.clearCollection')}
    </button>
    {#if cleared}
      <p class="help">{t('settings.collectionCleared')}</p>
    {/if}
  </section>
{/if}

<style>
  h1 {
    font-size: var(--step-3);
    margin: 1.5rem 0 2rem;
  }

  section {
    margin-bottom: 3rem;
    max-width: var(--measure);
  }

  h2 {
    font-size: var(--step-1);
    margin-bottom: 0.7em;
  }

  .choices {
    display: flex;
    gap: 0.5em;
  }

  .choices button {
    background: none;
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 0.3em 1em;
    color: var(--paper-dim);
  }

  .choices button.on {
    background: var(--brass);
    border-color: var(--brass);
    color: var(--ink-900);
    font-weight: 600;
  }

  .where {
    color: var(--paper-dim);
  }

  .toggle {
    display: flex;
    gap: 0.6em;
    align-items: flex-start;
    margin: 1.2rem 0;
  }

  .toggle input {
    margin-top: 0.3em;
  }

  .help {
    display: block;
    font-size: 0.85rem;
    color: var(--paper-dim);
    margin-top: 0.2em;
  }

  .out {
    background: none;
    border: 1px solid var(--oxblood);
    border-radius: var(--radius);
    padding: 0.4em 1.1em;
    color: var(--oxblood);
  }

  .out:hover:not(:disabled) {
    background: var(--oxblood);
    color: var(--paper);
  }

  .out:disabled {
    opacity: 0.6;
    cursor: default;
  }
</style>
