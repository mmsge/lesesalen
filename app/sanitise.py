"""Server-side sanitising of everything that came off somebody else's instance.

The client sanitises too (DOMPurify, same allowlist). That is not redundancy for
its own sake: this process parses ActivityPub JSON from arbitrary hosts, and the
browser holds a token in localStorage where one successful XSS is a full account
compromise. Two layers, deliberately (§9.3 of the brief).

Allowlist, never blocklist. `img`, `svg`, `iframe`, `object`, `embed`, `style`,
`math` and `form` are excluded on purpose — `svg` and `math` are the classic
mutation-XSS vectors, and images inside post content are unnecessary because
attachments arrive as structured fields.
"""
from __future__ import annotations

import html as _html

import nh3

ALLOWED_TAGS: set[str] = {
    "p", "br", "span", "a", "em", "strong", "b", "i", "del",
    "code", "pre", "blockquote", "ul", "ol", "li",
}

# Mastodon marks up mentions and hashtags with classes (`mention`, `hashtag`,
# `invisible`, `ellipsis`); links render wrong without them.
ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    # No "rel" here on purpose: `link_rel` below owns that attribute, and nh3
    # refuses to let both manage it. Letting nh3 own it is the stronger of the
    # two — a remote rel="" can never override what we force onto every link.
    "a": {"href", "class", "translate", "target"},
    "span": {"class", "translate"},
    "p": {"class", "translate"},
    "code": {"class"},
    "pre": {"class"},
    "blockquote": {"class"},
    "ul": {"class"},
    "ol": {"class"},
    "li": {"class"},
    "em": {"class"},
    "strong": {"class"},
    "del": {"class"},
}

ALLOWED_SCHEMES: set[str] = {"http", "https", "mailto"}


def clean_html(value: object) -> str:
    """Sanitise remote HTML down to the allowlist above.

    Links come back with `rel="nofollow noopener noreferrer"` — `noreferrer`
    also stops the destination learning which page the reader came from.
    """
    if not isinstance(value, str) or not value.strip():
        return ""
    return nh3.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_SCHEMES,
        link_rel="nofollow noopener noreferrer",
        strip_comments=True,
    )


def clean_text(value: object, *, limit: int = 2000) -> str:
    """Reduce remote markup to plain text.

    Used for fields the UI renders as text rather than markup — review titles,
    book titles, author names, content warnings. Tags are stripped and entities
    resolved, so the caller gets real text: rendering the result as text is
    safe, and rendering it as HTML would not be, which is why every caller of
    this function must bind it to a text node.
    """
    if not isinstance(value, str) or not value.strip():
        return ""
    stripped = nh3.clean(value, tags=set(), attributes={}, strip_comments=True)
    text = _html.unescape(stripped)
    text = " ".join(text.split())
    return text[:limit]
