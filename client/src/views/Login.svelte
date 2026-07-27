<script>
  /**
   * Logging in, in two screens (5a, 5b).
   *
   * **5a** is one field that takes either `markus@skvip.lol` or `skvip.lol`,
   * because people know their handle and not always their domain. Instances
   * this browser has used before are listed underneath with the software we
   * found; a brass dot means we have actually spoken to that host.
   *
   * **5b** says in plain language what is about to happen, before the reader
   * leaves the app — and the "Lesesalen kan ikkje" list is given exactly as much
   * room as the "ber om" list. A consent screen that only lists what it wants is
   * not a consent screen.
   */
  import Icon from '../components/Icon.svelte';
  import * as auth from '../lib/auth.js';
  import * as server from '../lib/server.js';
  import { recent, remember, suggest } from '../lib/instances.svelte.js';
  import { navigate } from '../lib/router.svelte.js';
  import { t } from '../lib/i18n.svelte.js';
  import { untrack } from 'svelte';

  let { prefill = '' } = $props();

  // `?instans=` fills the field once. After that the reader is typing in it, and
  // a derived value would fight them for the cursor.
  let typed = $state(untrack(() => prefill));
  let step = $state('instance');
  let busy = $state(false);
  let problem = $state(null);
  let suggestion = $state(null);

  const domain = $derived(auth.normaliseDomain(typed));

  const ASKS = ['login.askFollows', 'login.askWrite'];
  const CANNOTS = ['login.cannotDm', 'login.cannotFollow', 'login.cannotShelve'];

  async function check(event) {
    event?.preventDefault();
    problem = null;
    suggestion = null;
    if (!domain) {
      problem = 'login.errorDomain';
      suggestion = suggest(typed.split('@').pop());
      return;
    }
    busy = true;
    try {
      // One nodeinfo probe, so the consent screen can name real software rather
      // than sending the reader off to find out.
      const answers = await server.instances([domain]);
      const found = answers[domain] || {};
      remember(domain, {
        software: found.programvare || null,
        version: found.versjon || null,
        reached: Boolean(found.programvare),
      });
      if (!found.programvare) {
        problem = 'login.errorNotAnInstance';
        suggestion = suggest(domain);
        return;
      }
      step = 'consent';
    } catch {
      // The probe is a courtesy, not a gate: the instance itself is the
      // authority on whether it can be logged into.
      remember(domain, {});
      step = 'consent';
    } finally {
      busy = false;
    }
  }

  async function go() {
    busy = true;
    problem = null;
    try {
      await auth.begin(domain);
    } catch (error) {
      problem = String(error.message) === 'domain' ? 'login.errorDomain' : 'login.errorApps';
      busy = false;
      step = 'instance';
    }
  }
</script>

<div class="login fades">
  {#if step === 'instance'}
    <div class="pane lit">
      <p class="label">{t('app.name')}</p>
      <h1>{t('login.heading')}</h1>
      <p class="lead">{t('login.lead')}</p>

      <form onsubmit={check}>
        <label class="field">
          <span class="label dim">{t('login.domainLabel')}</span>
          <span class="input">
            <span class="at" aria-hidden="true">@</span>
            <input
              type="text"
              bind:value={typed}
              placeholder={t('login.domainPlaceholder')}
              autocomplete="url"
              autocapitalize="none"
              spellcheck="false"
              required
            />
          </span>
        </label>
        <p class="help">{t('login.domainHelp')}</p>

        {#if problem}
          <p class="bad">
            {t(problem)}
            {#if suggestion}
              <button type="button" class="did-you-mean" onclick={() => { typed = suggestion; check(); }}>
                {t('login.didYouMean', { domain: suggestion })}
              </button>
            {/if}
          </p>
        {/if}

        {#if recent.list.length}
          <p class="label dim">{t('login.recent')}</p>
          <ul class="recent">
            {#each recent.list as entry (entry.domain)}
              <li>
                <button type="button" onclick={() => { typed = entry.domain; check(); }}>
                  <span class="dot" class:known={entry.reached} aria-hidden="true"></span>
                  <span class="host">{entry.domain}</span>
                  {#if entry.software}
                    <span class="software">
                      {entry.software}{#if entry.version} {entry.version}{/if}
                    </span>
                  {:else}
                    <span class="software">{t('login.notProbed')}</span>
                  {/if}
                </button>
              </li>
            {/each}
          </ul>
        {/if}

        <button type="submit" class="primary" disabled={busy || !domain}>
          {busy ? t('login.working') : domain ? t('login.continueTo', { domain }) : t('login.submit')}
        </button>
        {#if domain}<p class="help">{t('login.passwordThere', { domain })}</p>{/if}
      </form>
    </div>
  {:else}
    <div class="pane">
      <div class="nav">
        <button type="button" class="chev" aria-label={t('nav.back')} onclick={() => (step = 'instance')}>
          <Icon name="back" size={20} />
        </button>
        <span class="where">{domain}</span>
      </div>

      <div class="lit inner">
        <h1>{t('login.consentHeading', { domain })}</h1>
        <p class="lead">{t('login.consentLead')}</p>

        <p class="label">{t('login.asksFor')}</p>
        <ul class="asks">
          {#each ASKS as key (key)}
            <li>
              <span class="tick"><Icon name="check" size={18} stroke={1.6} /></span>
              <span>
                <span class="what">{t(`${key}Title`)}</span>
                <span class="why">{t(`${key}Why`)}</span>
              </span>
            </li>
          {/each}
        </ul>

        <p class="label dim">{t('login.cannot')}</p>
        <ul class="cannots">
          {#each CANNOTS as key (key)}
            <li>
              <span class="nope"><Icon name="cross" size={18} /></span>
              <span class="what">{t(key)}</span>
            </li>
          {/each}
        </ul>

        <div class="choices">
          <button type="button" class="primary" onclick={go} disabled={busy}>
            {busy ? t('login.working') : t('login.open', { domain })}
          </button>
          <button type="button" class="secondary" onclick={() => navigate('/')}>
            {t('composer.cancel')}
          </button>
        </div>
        <p class="help">{t('login.tokenStays', { domain })}</p>
      </div>
    </div>
  {/if}
</div>

<style>
  .login {
    padding-bottom: calc(var(--tabbar) + var(--safe-bottom));
  }

  .pane {
    width: min(100%, var(--column));
    margin-inline: auto;
  }

  .lit {
    padding: calc(34px + var(--safe-top)) 22px 22px;
    background: radial-gradient(80% 100% at 50% -10%, rgba(201, 162, 39, 0.26), rgba(15, 13, 11, 0) 68%);
  }

  .inner {
    padding-top: 8px;
  }

  h1 {
    font-size: 1.7rem;
    line-height: 1.18;
    margin: 10px 0;
    color: var(--paper-bright);
  }

  .lead {
    margin: 0 0 18px;
    font-size: 0.95rem;
    color: var(--paper-dim);
  }

  .field {
    display: grid;
    gap: 8px;
  }

  .input {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 56px;
    padding: 0 14px;
    background: var(--panel);
    border: 1px solid var(--brass);
    border-radius: var(--radius);
  }

  .at {
    color: var(--paper-dim);
    font-size: 1.1rem;
  }

  input {
    flex: 1;
    min-width: 0;
    align-self: stretch;
    font: inherit;
    font-size: 1.15rem;
    color: var(--paper);
    background: none;
    border: 0;
    padding: 0;
  }

  input:focus {
    outline: none;
  }

  .help {
    margin: 10px 0 18px;
    font-size: 0.85rem;
    color: var(--paper-dim);
  }

  .bad {
    margin: 0 0 16px;
    font-size: 0.9rem;
    color: var(--warn);
  }

  .did-you-mean {
    display: inline-block;
    min-height: 44px;
    padding: 0 4px;
    background: none;
    border: 0;
    color: var(--brass);
    text-decoration: underline;
    text-underline-offset: 0.15em;
  }

  .label {
    margin-bottom: 10px;
  }

  .recent {
    list-style: none;
    margin: 0 0 18px;
    padding: 0;
    display: grid;
    gap: 1px;
    background: var(--rule);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    overflow: hidden;
  }

  .recent button {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    min-height: 52px;
    padding: 0 14px;
    background: var(--panel);
    border: 0;
    text-align: left;
  }

  /* Never colour alone: the software line beside it says the same thing. */
  .dot {
    flex: none;
    width: 8px;
    height: 8px;
    border-radius: 999px;
    border: 1.5px solid var(--paper-dim);
  }

  .dot.known {
    background: var(--brass);
    border-color: var(--brass);
  }

  .host {
    flex: 1;
    min-width: 0;
    font-size: 0.95rem;
    color: var(--paper);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .software {
    flex: none;
    font-size: 0.85rem;
    color: var(--paper-dim);
  }

  .nav {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: calc(14px + var(--safe-top)) 20px 12px;
    border-bottom: 1px solid var(--rule);
  }

  .chev {
    flex: none;
    width: 44px;
    height: 44px;
    margin-left: -10px;
    display: grid;
    place-items: center;
    background: none;
    border: 0;
    color: var(--paper-dim);
  }

  .where {
    font-size: 0.9rem;
    color: var(--paper-dim);
  }

  .asks,
  .cannots {
    list-style: none;
    margin: 0 0 22px;
    padding: 0;
    display: grid;
    gap: 14px;
  }

  .asks li,
  .cannots li {
    display: flex;
    gap: 14px;
    align-items: flex-start;
  }

  .tick {
    flex: none;
    color: var(--brass);
  }

  .nope {
    flex: none;
    color: var(--paper-dim);
  }

  .what {
    display: block;
    font-size: 1rem;
    color: var(--paper);
  }

  .why {
    display: block;
    margin-top: 2px;
    font-size: 0.88rem;
    color: var(--paper-dim);
  }

  .choices {
    display: grid;
    gap: 10px;
  }
</style>
