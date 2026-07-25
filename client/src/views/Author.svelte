<script>
  /**
   * One person's book posts.
   *
   * The one broadening the project allows: it is a normal client affordance, it
   * goes through the reader's own instance with the reader's own token, and it
   * shows exactly what Mastodon would show. No server involvement beyond the
   * same enrichment every other card gets.
   */
  import Card from '../components/Card.svelte';
  import Composer from '../components/Composer.svelte';
  import * as mastodon from '../lib/mastodon.js';
  import { postsByAccount } from '../lib/feed.svelte.js';
  import { navigate, route, link } from '../lib/router.svelte.js';
  import { plain } from '../lib/sanitise.js';
  import { t } from '../lib/i18n.svelte.js';

  let { account } = $props();

  let items = $state([]);
  let who = $state(null);
  let loading = $state(true);
  let problem = $state(false);
  let replyingTo = $state(null);

  const handle = $derived(decodeURIComponent(route.path.replace('/lesar/', '')));

  $effect(() => {
    let cancelled = false;
    loading = true;
    problem = false;
    (async () => {
      try {
        const found = await mastodon.lookupAccount(account, handle);
        if (cancelled) return;
        who = found;
        const posts = await postsByAccount(account, found.id);
        if (!cancelled) items = posts;
      } catch {
        if (!cancelled) problem = true;
      } finally {
        if (!cancelled) loading = false;
      }
    })();
    return () => {
      cancelled = true;
    };
  });

  const name = $derived(plain(who?.display_name) || who?.username || handle);
</script>

<p class="back"><a href="/" use:link>{t('author.back')}</a></p>

<h1>{t('author.heading', { name })}</h1>
<p class="lead">{t('author.lead')}</p>

{#if replyingTo}
  <Composer item={replyingTo} {account} onclose={() => (replyingTo = null)} />
{/if}

{#if loading}
  <p class="notice">{t('author.loading')}</p>
{:else if problem}
  <p class="notice bad">{t('error.generic')}</p>
{:else if !items.length}
  <p class="notice">{t('author.empty')}</p>
{:else}
  <div class="column">
    {#each items as item (item.core.uri)}
      <Card
        {item}
        {account}
        onperson={(target) => navigate(`/lesar/${encodeURIComponent(target.acct)}`)}
        onreply={(target) => (replyingTo = target)}
      />
    {/each}
  </div>
{/if}

<style>
  .back {
    margin: 1.5rem 0 0.5rem;
    font-size: 0.85rem;
  }

  h1 {
    font-size: var(--step-3);
    margin: 0 0 0.2em;
  }

  .lead {
    color: var(--paper-dim);
    margin: 0 0 2rem;
    max-width: var(--measure);
  }

  .column {
    display: grid;
    gap: 1.5rem;
    margin-bottom: 4rem;
  }

  .notice {
    color: var(--paper-dim);
    margin: 2rem 0 4rem;
  }

  .notice.bad {
    color: var(--oxblood);
  }
</style>
