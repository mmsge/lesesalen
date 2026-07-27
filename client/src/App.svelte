<script>
  /**
   * Routing, the tab bar, and the two overlays every screen can raise.
   *
   * The route table (5g):
   *
   *   /                        the reading room; logged out it is the landing
   *   /?type=&bok=&person=     the same, filtered — the filters round-trip
   *   /@handle@host            one person's shelf. Public: no session needed
   *   /innlegg/<id>            one post, id = base64url of the object URI
   *   /bok/<work-id>           the book sheet; a page of its own on a direct link
   *   /logg-inn                which instance
   *   /logg-inn/attende        the OAuth callback, replaced out of history
   *   /innstillingar           settings
   *   /om, /personvern         text pages. Public
   *
   * Back never traps. A sheet is a history entry, so back closes it and leaves
   * the feed alone; a filter change is a history entry, so back removes it; and
   * a feed with no filters is the last entry before the app.
   */
  import Feed from './views/Feed.svelte';
  import Landing from './views/Landing.svelte';
  import About from './views/About.svelte';
  import Privacy from './views/Privacy.svelte';
  import Settings from './views/Settings.svelte';
  import Person from './views/Person.svelte';
  import PostDetail from './views/PostDetail.svelte';
  import Login from './views/Login.svelte';
  import Tabs from './components/Tabs.svelte';
  import Toast from './components/Toast.svelte';
  import BookSheet from './components/BookSheet.svelte';
  import FilterSheet from './components/FilterSheet.svelte';
  import Composer from './components/Composer.svelte';
  import * as auth from './lib/auth.js';
  import { feed, forget } from './lib/collection.svelte.js';
  import { flush, forgetQueue } from './lib/queue.svelte.js';
  import { forgetPrefs } from './lib/prefs.svelte.js';
  import { forgetInstances } from './lib/instances.svelte.js';
  import { net } from './lib/net.svelte.js';
  import { parse, count, toQuery, apply, handleOf } from './lib/filters.js';
  import { encodeId } from './lib/ids.js';
  import { inferQuiet } from './lib/stale.js';
  import { route, navigate, back, currentKey, pushEntry, link } from './lib/router.svelte.js';
  import { t } from './lib/i18n.svelte.js';

  let account = $state(auth.current());
  let loginProblem = $state(null);
  let returning = $state(route.path === '/logg-inn/attende' || route.path === '/attende');

  // Overlays. Each one records the history entry it was opened on, so a filter
  // change made *inside* the filter sheet does not look like a dismissal.
  let filterSheet = $state(null);
  let composerFor = $state(null);

  const filters = $derived(parse(route.query));
  const person = $derived(route.path.startsWith('/@') ? decodeURIComponent(route.path.slice(2)) : null);
  const detailId = $derived(
    route.path.startsWith('/innlegg/') ? decodeURIComponent(route.path.slice(9)) : null,
  );
  const bookId = $derived(
    route.path.startsWith('/bok/') ? decodeURIComponent(route.path.slice(5)) : null,
  );

  const tab = $derived(
    route.path === '/innstillingar' ? 'settings' : filterSheet !== null ? 'filter' : 'feed',
  );

  const sheetBook = $derived(
    bookId ? feed.books[bookId] || feed.items.find((i) => i.enrichment.bok === bookId)?.book : null,
  );
  const sheetBookPosts = $derived(
    bookId ? feed.items.filter((item) => item.enrichment.bok === bookId).length : 0,
  );

  // The whole collection as the filter sheet sees it, inferred items included,
  // so its counts agree with the feed's.
  const all = $derived.by(() => {
    const inferred = inferQuiet(feed.items);
    return inferred.length ? [...feed.items, ...inferred] : feed.items;
  });
  const shown = $derived(apply(all, filters).length);

  // Going back past the entry a sheet was opened on closes it. Going back to an
  // *earlier* filter while it is open does not.
  $effect(() => {
    function onpop() {
      const key = currentKey();
      if (filterSheet !== null && key < filterSheet) filterSheet = null;
      if (composerFor !== null && key < composerFor.entry) composerFor = null;
    }
    window.addEventListener('popstate', onpop);
    return () => window.removeEventListener('popstate', onpop);
  });

  /**
   * The OAuth callback (5c). `complete()` strips the code from the URL before
   * doing anything else, so it never lingers in history or a referrer, and the
   * reader lands in the first sweep rather than in an empty feed.
   */
  $effect(() => {
    if (route.path !== '/logg-inn/attende' && route.path !== '/attende') return;
    (async () => {
      try {
        account = await auth.complete(window.location.search);
        loginProblem = null;
        navigate('/', {}, { replace: true });
      } catch (error) {
        const reason = String(error.message);
        loginProblem =
          reason === 'avvist'
            ? 'login.errorDenied'
            : reason === 'state'
              ? 'login.errorState'
              : 'login.errorToken';
        navigate('/logg-inn', {}, { replace: true });
      } finally {
        returning = false;
      }
    })();
  });

  // Anything queued while the network was away goes out when it comes back.
  $effect(() => {
    if (net.online && account) flush(account);
  });

  function onlogout() {
    account = null;
    // Logging out clears everything this browser was keeping for the reader:
    // the collection, the queue, the drafts, the preferences, the instance list
    // (ADR 0009).
    forget();
    forgetQueue();
    forgetPrefs();
    forgetInstances();
    navigate('/');
  }

  function onopen(item) {
    if (item.inferred) return; // there is no post behind a derived line
    navigate(`/innlegg/${encodeId(item.core.uri)}`);
  }

  function onperson(who) {
    const handle = typeof who === 'string' ? who : handleOf(who);
    if (handle) navigate(`/@${handle}`);
  }

  function onbook(book) {
    if (book?.id) navigate(`/bok/${encodeURIComponent(book.id)}`);
  }

  function onreply(item) {
    // A queued draft comes back as a bare `{ uri }`; find the real card for it.
    const target = item.core ? item : feed.items.find((held) => held.core.uri === item.uri);
    if (!target) return;
    composerFor = { item: target, entry: pushEntry() };
  }

  function ontab(next) {
    if (next === 'settings') {
      navigate('/innstillingar');
      return;
    }
    if (next === 'feed') {
      filterSheet = null;
      if (route.path !== '/') navigate('/', toQuery(filters));
      return;
    }
    if (next === 'filter' && filterSheet === null) filterSheet = pushEntry();
  }
</script>

<a class="skip" href="#innhald">{t('app.skipToContent')}</a>

<Tabs
  {tab}
  filters={count(filters)}
  filterEnabled={Boolean(account) && feed.shelves > 0}
  onselect={ontab}
/>

<main id="innhald">
  {#if returning}
    <p class="notice">{t('login.returning')}</p>
  {:else if route.path === '/om'}
    <div class="text-page"><About /></div>
  {:else if route.path === '/personvern'}
    <div class="text-page"><Privacy /></div>
  {:else if route.path === '/logg-inn'}
    {#if loginProblem}<p class="notice bad">{t(loginProblem)}</p>{/if}
    <Login prefill={route.query.instans || ''} />
  {:else if route.path === '/innstillingar'}
    <Settings {account} {onlogout} />
  {:else if person}
    <Person handle={person} {account} {onopen} {onperson} {onbook} {onreply} />
  {:else if detailId}
    <PostDetail id={detailId} {account} {onperson} {onbook} {onreply} />
  {:else if account}
    <Feed {account} {filters} {onopen} {onperson} {onbook} {onreply} />
  {:else}
    <Landing />
  {/if}
</main>

{#if bookId}
  {#if sheetBook}
    <BookSheet
      book={sheetBook}
      posts={sheetBookPosts}
      onclose={() => back()}
      onfilter={(book) => {
        back();
        navigate('/', toQuery({ ...filters, book: book.id }));
      }}
    />
  {:else}
    <div class="notice">
      <p>{t('book.notHere')}</p>
      <a href="/" use:link>{t('nav.backToFeed')}</a>
    </div>
  {/if}
{/if}

{#if filterSheet !== null}
  <FilterSheet
    {filters}
    items={all}
    books={feed.books}
    {shown}
    total={all.length}
    onclose={() => back()}
  />
{/if}

{#if composerFor}
  <Composer item={composerFor.item} {account} onclose={() => back()} />
{/if}

<Toast />

<style>
  .skip {
    position: absolute;
    left: -9999px;
    top: 0;
    display: grid;
    place-items: center;
    min-height: 44px;
    background: var(--brass);
    color: var(--ink);
    padding: 0.5em 1em;
    z-index: 50;
  }

  .skip:focus {
    left: 0;
  }

  .text-page {
    width: min(100% - 2.5rem, var(--column));
    margin-inline: auto;
    padding-top: calc(1.5rem + var(--safe-top));
    padding-bottom: calc(var(--tabbar) + 2rem + var(--safe-bottom));
  }

  .notice {
    width: min(100% - 2.5rem, var(--column));
    margin: 3rem auto;
    color: var(--paper-dim);
  }

  .notice.bad {
    color: var(--warn);
  }
</style>
