<script>
  /**
   * Routing and the one piece of global state: whether somebody is logged in.
   *
   * One account at a time, no account switching.
   */
  import Feed from './views/Feed.svelte';
  import Landing from './views/Landing.svelte';
  import About from './views/About.svelte';
  import Privacy from './views/Privacy.svelte';
  import Settings from './views/Settings.svelte';
  import Author from './views/Author.svelte';
  import * as auth from './lib/auth.js';
  import { reset } from './lib/feed.svelte.js';
  import { route, navigate, link } from './lib/router.svelte.js';
  import { t } from './lib/i18n.svelte.js';

  let account = $state(auth.current());
  let returning = $state(route.path === '/attende');
  let loginProblem = $state(null);

  // The OAuth callback. `complete()` strips the code from the URL before doing
  // anything else, so it never lingers in history or a referrer.
  $effect(() => {
    if (route.path !== '/attende') return;
    (async () => {
      try {
        account = await auth.complete(window.location.search);
        navigate('/');
      } catch (error) {
        const reason = String(error.message);
        loginProblem =
          reason === 'avvist'
            ? 'login.errorDenied'
            : reason === 'state'
              ? 'login.errorState'
              : 'login.errorToken';
        navigate('/innstillingar');
      } finally {
        returning = false;
      }
    })();
  });

  function onlogout() {
    account = null;
    reset();
    navigate('/');
  }

  const isAuthor = $derived(route.path.startsWith('/lesar/'));
</script>

<a class="skip" href="#innhald">{t('app.skipToContent')}</a>

<header>
  <div class="inner">
    <a class="brand" href="/" use:link>
      <span class="name">{t('app.name')}</span>
      <span class="tagline">{t('app.tagline')}</span>
    </a>
    <nav>
      <a href="/om" use:link class:on={route.path === '/om'}>{t('nav.about')}</a>
      <a href="/personvern" use:link class:on={route.path === '/personvern'}>{t('nav.privacy')}</a>
      <a href="/innstillingar" use:link class:on={route.path === '/innstillingar'}>
        {account ? t('nav.settings') : t('nav.logIn')}
      </a>
    </nav>
  </div>
</header>

<main id="innhald">
  <div class="inner">
    {#if returning}
      <p class="notice">{t('login.returning')}</p>
    {:else if loginProblem && route.path === '/innstillingar'}
      <p class="notice bad">{t(loginProblem)}</p>
      <Settings {account} {onlogout} />
    {:else if route.path === '/om'}
      <About />
    {:else if route.path === '/personvern'}
      <Privacy />
    {:else if route.path === '/innstillingar'}
      <Settings {account} {onlogout} />
    {:else if isAuthor}
      {#if account}
        <Author {account} />
      {:else}
        <Landing />
      {/if}
    {:else if account}
      <Feed {account} />
    {:else}
      <Landing />
    {/if}
  </div>
</main>

<footer>
  <div class="inner">
    <p>
      <a href="/om" use:link>{t('nav.about')}</a>
      <a href="/personvern" use:link>{t('nav.privacy')}</a>
      <a href="https://github.com/mmsge/lesesalen" rel="noopener noreferrer" target="_blank">
        Kjeldekode
      </a>
    </p>
  </div>
</footer>

<style>
  .skip {
    position: absolute;
    left: -9999px;
    top: 0;
    background: var(--brass);
    color: var(--ink-900);
    padding: 0.5em 1em;
    z-index: 20;
  }

  .skip:focus {
    left: 0;
  }

  .inner {
    width: min(100% - 2.5rem, var(--column));
    margin-inline: auto;
  }

  header {
    border-bottom: 1px solid var(--rule);
  }

  header .inner {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    padding: 1.2rem 0;
  }

  .brand {
    text-decoration: none;
    color: inherit;
    display: grid;
    gap: 0.1em;
  }

  .name {
    font-family: var(--serif);
    font-size: var(--step-2);
    color: var(--paper);
    letter-spacing: 0.01em;
  }

  .tagline {
    font-size: 0.82rem;
    color: var(--paper-dim);
  }

  nav {
    display: flex;
    gap: 1.1rem;
    font-size: 0.9rem;
  }

  nav a {
    color: var(--paper-dim);
    text-decoration: none;
  }

  nav a:hover,
  nav a.on {
    color: var(--brass);
  }

  main .inner {
    /* The quotation card bleeds by this much on each side. */
    --bleed: 1.5rem;
  }

  .notice {
    margin: 3rem 0;
    color: var(--paper-dim);
  }

  .notice.bad {
    color: var(--oxblood);
  }

  footer {
    border-top: 1px solid var(--rule);
    padding: 1.5rem 0 3rem;
    margin-top: 3rem;
  }

  footer p {
    display: flex;
    gap: 1.2rem;
    margin: 0;
    font-size: 0.85rem;
  }

  footer a {
    color: var(--paper-dim);
    text-decoration: none;
  }

  footer a:hover {
    color: var(--brass);
  }
</style>
