# 0012 — A page number is a page number only when `positionMode` says `PG`

- **Status:** Accepted
- **Date:** 2026-07-27
- **Contributors:** Claude (agent decision — no human input on the technical
  choice; the mobile redesign handoff stated the rule, this record explains why
  the server had to change for the client to be able to keep it)
- **Topics:** bookwyrm, activitypub, data-contract, ui

## Context

The mobile redesign draws "side 143 av 320" as a real element of the comment and
quotation cards, and colours the comment card's left margin rule **brass when a
post has reading progress and grey when it does not**. Both are supposed to be
rare: most book posts carry no position at all, and the grey margin rule is the
normal case.

They were not rare. Almost every post that carried a `position` at all rendered a
page number, including posts where the number meant something else entirely.

The cause was one line in `app/enrich.py`:

```python
def _position_mode(value: Any) -> str:
    if isinstance(value, str) and value.strip().lower() in {"pct", "percent", "prosent"}:
        return "prosent"
    return "side"          # ← everything else, including "absent"
```

BookWyrm sends `positionMode: "PG"` for a page number and `"PCT"` for a
percentage, and **most objects send neither**. Defaulting the absent case to
`"side"` turned "this post does not say where the reader is" into "this post is
on page N". The client had no way to tell the two apart: by the time the
enrichment dict reached the browser, the distinction was gone.

Rendering a made-up page number is not a cosmetic bug. It is the app stating,
in a book's own card, a fact about somebody's reading that nobody ever said.

## Decision

**`posisjonsmodus` is `"side"`, `"prosent"` or `None`, and `None` is the common
case.** `_position_mode` returns a mode only for a value that names one:

- `PG`, `page`, `pages`, `side` → `"side"`
- `PCT`, `percent`, `prosent` → `"prosent"`
- anything else, including absent → `None`

**One predicate decides, and everything asks it.** `client/src/lib/progress.js`
exports `hasProgress(enrichment)`, which is true only when `posisjon` is a number
*and* `posisjonsmodus === 'side'`. `Progress.svelte` renders nothing otherwise;
`CommentCard.svelte` colours its margin rule from the same call; the quotation
card's "Is-slottet, s. 41" drops to "Is-slottet" from the same call. There is no
second place where the question is answered.

The percentage preference in Settings computes from the page number and the
edition's page count. It is a display of a real position, never a source of one.

## Consequences

- **Most comment cards now have a grey margin rule**, which is what the design
  says the norm looks like. A brass one means the post really did say a page.
- **A `position` with no mode is dropped from the UI**, not guessed at. It is
  still in the enrichment dict for anything that later learns what it means.
- **The trap.** `_position_mode` returning `str | None` looks like an oversight:
  the obvious "tidy-up" is to give it a default so callers do not have to handle
  `None`, and `"side"` is the natural-looking default. That single change puts
  invented page numbers back on screen, with no error anywhere and nothing
  visibly broken — the numbers are real, they simply are not page numbers.
  `test_absent_position_mode_is_none_not_pages` and
  `test_bookwyrm_pg_position_mode_is_pages` pin both directions.
- **The client-side trap.** Reading `enrichment.posisjon` directly instead of
  calling `hasProgress` reintroduces the same bug one component at a time. Any
  new surface that shows progress goes through `lib/progress.js`.
