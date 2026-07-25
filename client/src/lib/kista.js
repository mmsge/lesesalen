/**
 * Kista — where the reader's collection is kept between visits.
 *
 * Walking the outboxes of everybody you follow is expensive the first time: one
 * throttled request per actor before a screen exists, and a further lookup for
 * every book edition nobody has fetched before. Doing that again on every reload
 * is rude to the origin instances and slow for the reader, so the assembled
 * collection is remembered here.
 *
 * This does not contradict ADR 0005. That record is about *our server* not
 * accumulating a corpus of other people's reading. This is the reader's own feed,
 * on the reader's own machine, under their control — what every fediverse client
 * does, and what their Mastodon web UI already does. See ADR 0009.
 *
 * **Ephemeral mode writes nothing.** If the reader ticked "log me out when I
 * close the tab" they are on a shared machine, and a durable on-disk archive of
 * other people's reading is the opposite of what they asked for. `open()` returns
 * null and every operation here becomes a no-op.
 *
 * Every write is best-effort. Private-browsing modes and exhausted quotas make
 * IndexedDB throw, and a reader with no usable storage should get the in-memory
 * experience rather than an error.
 */
import { isEphemeral } from './storage.js';

const NAME = 'lesesalen';
// 2: posts stored by v1 have no `publisert` — the server was not returning the
// origin's publication time, so every card dated from the epoch and the sort was
// meaningless. Those rows cannot be repaired locally, so the upgrade drops them
// and the next sweep refetches. Bump this again for any change that invalidates
// stored rows rather than trying to migrate them: a re-sweep is cheap now.
const VERSION = 2;

export const POSTS = 'postar';
export const ACTORS = 'aktorar';
export const BOOKS = 'boker';

// A cap, so a reader who follows thirty prolific accounts does not fill their
// disk. Oldest posts go first: the collection is a reading feed, not an archive,
// and ADR 0009 leans on this eviction to bound how stale it can get.
export const MAX_POSTS = 6000;

let opening = null;

function request(action) {
  return new Promise((resolve, reject) => {
    let query;
    try {
      query = action();
    } catch (error) {
      reject(error);
      return;
    }
    query.onsuccess = () => resolve(query.result);
    query.onerror = () => reject(query.error);
  });
}

/** The database, or null when there must not be one. */
export function open() {
  if (isEphemeral()) return Promise.resolve(null);
  if (opening) return opening;
  opening = new Promise((resolve) => {
    let request;
    try {
      request = window.indexedDB.open(NAME, VERSION);
    } catch {
      resolve(null);
      return;
    }
    request.onupgradeneeded = (event) => {
      const database = request.result;
      // Rows from before this version are not worth migrating — drop and re-sweep.
      if (event.oldVersion > 0 && database.objectStoreNames.contains(POSTS)) {
        database.deleteObjectStore(POSTS);
        if (database.objectStoreNames.contains(ACTORS)) database.deleteObjectStore(ACTORS);
      }
      if (!database.objectStoreNames.contains(POSTS)) {
        const posts = database.createObjectStore(POSTS, { keyPath: 'uri' });
        // Sorting and eviction both work on publication date.
        posts.createIndex('publisert', 'publisert');
      }
      if (!database.objectStoreNames.contains(ACTORS)) {
        database.createObjectStore(ACTORS, { keyPath: 'aktor' });
      }
      if (!database.objectStoreNames.contains(BOOKS)) {
        database.createObjectStore(BOOKS, { keyPath: 'id' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => resolve(null);
    request.onblocked = () => resolve(null);
  });
  return opening;
}

async function transact(stores, mode, work) {
  const database = await open();
  if (!database) return null;
  try {
    const transaction = database.transaction(stores, mode);
    const result = await work(transaction);
    if (mode === 'readwrite') {
      await new Promise((resolve) => {
        transaction.oncomplete = resolve;
        transaction.onerror = resolve; // quota: not fatal, just not remembered
        transaction.onabort = resolve;
      });
    }
    return result;
  } catch {
    return null;
  }
}

/** Everything remembered, in one read. */
export async function loadAll() {
  const empty = { posts: [], actors: [], books: [] };
  const loaded = await transact([POSTS, ACTORS, BOOKS], 'readonly', async (transaction) => ({
    posts: await request(() => transaction.objectStore(POSTS).getAll()),
    actors: await request(() => transaction.objectStore(ACTORS).getAll()),
    books: await request(() => transaction.objectStore(BOOKS).getAll()),
  }));
  return loaded || empty;
}

export async function putPosts(rows) {
  if (!rows.length) return;
  await transact([POSTS], 'readwrite', (transaction) => {
    const store = transaction.objectStore(POSTS);
    for (const row of rows) store.put(row);
  });
}

export async function putActor(row) {
  await transact([ACTORS], 'readwrite', (transaction) => {
    transaction.objectStore(ACTORS).put(row);
  });
}

export async function putBooks(books) {
  const rows = Object.values(books || {}).filter((book) => book && book.id);
  if (!rows.length) return;
  await transact([BOOKS], 'readwrite', (transaction) => {
    const store = transaction.objectStore(BOOKS);
    for (const row of rows) store.put(row);
  });
}

/** Drop the oldest posts once the collection outgrows its cap. */
export async function prune(max = MAX_POSTS) {
  await transact([POSTS], 'readwrite', async (transaction) => {
    const store = transaction.objectStore(POSTS);
    const count = await request(() => store.count());
    let excess = count - max;
    if (excess <= 0) return;
    // Walk the date index forwards: oldest first.
    await new Promise((resolve) => {
      const cursorQuery = store.index('publisert').openCursor();
      cursorQuery.onsuccess = () => {
        const cursor = cursorQuery.result;
        if (!cursor || excess <= 0) {
          resolve();
          return;
        }
        cursor.delete();
        excess -= 1;
        cursor.continue();
      };
      cursorQuery.onerror = () => resolve();
    });
  });
}

/** Forget the whole collection. Called on log-out and from Settings. */
export async function clear() {
  await transact([POSTS, ACTORS, BOOKS], 'readwrite', (transaction) => {
    transaction.objectStore(POSTS).clear();
    transaction.objectStore(ACTORS).clear();
    transaction.objectStore(BOOKS).clear();
  });
}

/**
 * Delete the database outright.
 *
 * Used when the reader switches *into* ephemeral mode: `clear()` would need an
 * open handle, and from that moment on `open()` refuses to give one. The stored
 * collection must still go.
 */
export function destroy() {
  opening = null;
  return new Promise((resolve) => {
    try {
      const request = window.indexedDB.deleteDatabase(NAME);
      request.onsuccess = () => resolve();
      request.onerror = () => resolve();
      request.onblocked = () => resolve();
    } catch {
      resolve();
    }
  });
}
