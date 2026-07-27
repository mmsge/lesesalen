/**
 * Whether there is a network. Nothing more.
 *
 * Offline is not an error state in this app: the collection in the browser is
 * still a whole library, so the reader gets a grey dot and the word "Utan nett"
 * and carries on reading. What changes is that we stop *attempting* requests —
 * a queue of failing fetches produces nothing but noise — and replies go into
 * the outbox queue instead.
 */
export const net = $state({ online: navigator.onLine !== false });

window.addEventListener('online', () => {
  net.online = true;
});

window.addEventListener('offline', () => {
  net.online = false;
});
