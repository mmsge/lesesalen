/**
 * Client-side sanitising of remote HTML.
 *
 * The server sanitises the same content with the same allowlist (app/sanitise.py).
 * This is the second layer, and it is the one that matters most: the token lives
 * in localStorage, so one successful XSS is a full account compromise for
 * whoever is using the app.
 *
 * THE RULE, which a well-meaning refactor is most likely to break:
 * never pass remote content to `{@html}` without running it through `rich()`
 * first. If you are reaching for `{@html}` and the value did not come out of
 * this file, stop.
 */
import DOMPurify from 'dompurify';

const ALLOWED_TAGS = [
  'p', 'br', 'span', 'a', 'em', 'strong', 'b', 'i', 'del',
  'code', 'pre', 'blockquote', 'ul', 'ol', 'li',
];

// Mastodon uses `mention`, `hashtag`, `invisible` and `ellipsis`; links render
// wrong without the class attribute.
const ALLOWED_ATTR = ['href', 'rel', 'class', 'translate', 'target'];

let configured = false;

function configure() {
  if (configured) return;
  // Force every link safe. `noreferrer` also stops the destination learning
  // which page the reader came from.
  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (node.tagName === 'A') {
      node.setAttribute('rel', 'nofollow noopener noreferrer');
      node.setAttribute('target', '_blank');
    }
  });
  configured = true;
}

/** Sanitise remote HTML for `{@html}`. Allowlist only, never a blocklist. */
export function rich(html) {
  if (typeof html !== 'string' || html === '') return '';
  configure();
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    // http, https and mailto only — javascript:, data: and vbscript: are out.
    ALLOWED_URI_REGEXP: /^(?:https?|mailto):/i,
    // svg and math are mutation-XSS vectors; images inside post content are
    // unnecessary because attachments arrive as structured fields.
    FORBID_TAGS: ['img', 'svg', 'math', 'iframe', 'object', 'embed', 'style', 'form'],
    FORBID_ATTR: ['style', 'srcset', 'formaction'],
    USE_PROFILES: { html: true },
    RETURN_TRUSTED_TYPE: false,
  });
}

/**
 * Reduce remote markup to plain text.
 *
 * For anything the UI binds to a text node: display names, `spoiler_text`,
 * book titles. `spoiler_text` in particular is plain text in the API and must
 * be escaped, not parsed.
 */
export function plain(value) {
  if (typeof value !== 'string' || value === '') return '';
  configure();
  const stripped = DOMPurify.sanitize(value, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
  const holder = document.createElement('textarea');
  holder.innerHTML = stripped;
  return holder.value.replace(/\s+/g, ' ').trim();
}
