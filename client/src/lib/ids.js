/**
 * A post's address: `/innlegg/<base64url of the object URI>`.
 *
 * The URI is the only stable identifier a card collected from an outbox has —
 * there is no Mastodon status id until somebody interacts with it, and there
 * never is one on an instance the reader is not on. Base64url keeps it in one
 * path segment without percent-encoding a URL inside a URL, which is unreadable
 * in an address bar and gets mangled by everything that touches links.
 *
 * This is an encoding, not a secret: it is reversible on purpose, so a shared
 * link resolves against whatever the recipient's own collection holds.
 */
export function encodeId(uri) {
  if (typeof uri !== 'string' || !uri) return '';
  const bytes = new TextEncoder().encode(uri);
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function decodeId(id) {
  if (typeof id !== 'string' || !id) return null;
  try {
    const padded = id.replace(/-/g, '+').replace(/_/g, '/');
    const binary = atob(padded + '='.repeat((4 - (padded.length % 4)) % 4));
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  } catch {
    return null;
  }
}
