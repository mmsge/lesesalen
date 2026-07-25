# 0007 — BookWyrm serves third parties a plain `Note`; the URI is the type

- **Status:** Accepted
- **Date:** 2026-07-25
- **Contributors:** Claude (agent decision — no human input on the technical
  choice; discovered by fetching real objects from bookwyrm.social rather than
  from the protocol documentation)
- **Topics:** activitypub, bookwyrm, parsing, incident, federation

## Context

The premise of the whole project is that Mastodon discards BookWyrm's rich
fields, but the origin object still has them, so re-fetching the object with
`Accept: application/activity+json` recovers the rating, the review title, the
quoted passage, the position and the book link.

That is true, but only partly, and the part that is *not* true is the part the
parser was originally built on.

**What real objects actually look like.** Fetched unauthenticated from
`bookwyrm.social`, both of these come back with `"type": "Note"`:

```
https://bookwyrm.social/user/mvrkws/generatednote/12091719   -> type: Note
https://bookwyrm.social/user/mvrkws/comment/11996174         -> type: Note
```

BookWyrm serialises two representations of every status: a rich one for other
BookWyrm servers (`type: "Review"`, with `rating`, `name`, `quote`) and a
**"pure"** one for everybody else, where the type collapses to `Note` and the
rich fields are folded into the rendered `content`. Third-party fetches — all we
ever do — get the pure form. Sending a `User-Agent` carrying a BookWyrm version
marker was tested and did **not** change the response; it was not pursued
further, because claiming to be BookWyrm would be dishonest and the brief calls
for an honest User-Agent.

Trusting the `type` field therefore classifies **every post on bookwyrm.social**
as a plain note, and the five card types collapse into one.

**But the URI still says what the object is** — as the brief noted from the
start, the URI encodes its own type:

```
/user/x/review/1   /user/x/quotation/2   /user/x/comment/3   /user/x/generatednote/4
```

Two more things were learned the same way, both good news:

- **`readingStatus` is a real machine-readable field** (`to-read`, `reading`,
  `read`, `stopped-reading`), so reading states do not have to be recovered by
  regex over English prose after all. The prose match survives only as a
  fallback for objects that omit it.
- **The book link is in three different places** depending on the kind:
  `inReplyToBook` on comments/reviews/quotations, a `tag` entry of type
  `Edition` on generated notes, and sometimes only as an `<a href>` inside the
  content.

## Decision

- **The URI path segment is the primary type discriminator**
  (`enrich.kind_from_uri`). The `type` field is a refinement used only when an
  instance does serve the rich form.
- **Rich fields are read when present and reconstructed when not.** In the pure
  representation a review's `name` is
  `Review of "The Book" (4 stars): the real title`, which is the only surviving
  home of the rating — both the rating and the real title are recovered from it.
  A pure quotation's passage arrives in `content`, so it is promoted to the
  quote slot rather than rendered as body text.
- **The book URL is resolved through all three shapes**, in order:
  `inReplyToBook`, then an `Edition` tag, then a same-host `/book/<id>` link in
  the content. Cross-host links are ignored in every case.
- **`readingStatus` wins over the prose match** when both are available.

## Consequences

- Everything degrades rather than breaking. An unrecognised URI segment plus a
  bare `Note` with a book link is treated as a comment; an unmatched reading
  state renders the generic reading-status strip. A degraded card always beats a
  missing one.
- The parser is tested against the real shapes observed from bookwyrm.social,
  not against the idealised protocol (`tests/test_enrich.py`, the
  "pure representation" section).
- **Do not "simplify" the classifier to trust `type`.** It will look correct in
  a unit test written from the ActivityPub vocabulary and will misclassify every
  real post.
- If BookWyrm ever serves the rich form to third parties, nothing breaks: the
  `type` refinement and the direct `rating`/`quote`/`name` reads already handle
  it, and the reconstruction paths simply stop firing.
