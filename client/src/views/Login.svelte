<script>
  /** Enter a domain, get handed to that instance. Nothing is sent to us. */
  import * as auth from '../lib/auth.js';
  import { t } from '../lib/i18n.svelte.js';

  let domain = $state('');
  let busy = $state(false);
  let problem = $state(null);

  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    problem = null;
    if (!auth.normaliseDomain(domain)) {
      problem = 'login.errorDomain';
      return;
    }
    busy = true;
    try {
      await auth.begin(domain);
    } catch (error) {
      problem = String(error.message) === 'domain' ? 'login.errorDomain' : 'login.errorApps';
      busy = false;
    }
  }
</script>

<form class="login" onsubmit={submit}>
  <h2>{t('login.heading')}</h2>
  <p class="lead">{t('login.lead')}</p>

  <label class="field">
    <span class="label">{t('login.domainLabel')}</span>
    <input
      type="text"
      bind:value={domain}
      placeholder={t('login.domainPlaceholder')}
      autocomplete="url"
      autocapitalize="none"
      spellcheck="false"
      required
    />
    <span class="help">{t('login.domainHelp')}</span>
  </label>

  {#if problem}<p class="bad">{t(problem)}</p>{/if}

  <button type="submit" disabled={busy}>{busy ? t('login.working') : t('login.submit')}</button>
</form>

<style>
  .login {
    display: grid;
    gap: 1rem;
    max-width: var(--measure);
    margin: 2rem 0 4rem;
    padding: 1.5rem;
    background: var(--ink-800);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
  }

  h2 {
    margin: 0;
    font-size: var(--step-2);
  }

  .lead {
    margin: 0;
    color: var(--paper-dim);
  }

  .field {
    display: grid;
    gap: 0.3em;
  }

  .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--paper-dim);
  }

  input {
    font: inherit;
    color: var(--paper);
    background: var(--ink-900);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 0.5em 0.7em;
  }

  input:focus {
    border-color: var(--brass);
  }

  .help {
    font-size: 0.82rem;
    color: var(--paper-dim);
  }

  .bad {
    margin: 0;
    color: var(--oxblood);
  }

  button {
    justify-self: start;
    background: var(--brass);
    color: var(--ink-900);
    border: 1px solid var(--brass);
    border-radius: var(--radius);
    padding: 0.45em 1.2em;
    font-weight: 600;
  }

  button:disabled {
    opacity: 0.6;
    cursor: default;
  }
</style>
