# 0014 — A book's cloth and silhouette are a pure function of its work id

- **Status:** Accepted
- **Date:** 2026-07-27
- **Contributors:** Claude (agent decision — no human input on the technical
  choice; the mobile redesign handoff required determinism and named the
  placeholder implementation as unsuitable)
- **Topics:** ui, design, bookwyrm

## Context

Most books in a BookWyrm feed have no cover art we can show. The redesign fills
that space with a synthesised jacket — binding cloth, a spine gutter, the title
in Literata — and the feed's "På hylla no" strip draws the same books as spines
standing on a shelf rail, each with its own width and height.

That only works if a book looks the *same* every time. The shelf strip is meant
to be recognisable at a glance: the tall green one is the one you were reading.
A jacket whose colour changes between the feed and the book sheet, or whose
width changes when the sweep happens to return posts in a different order, is
just noise where a memory aid was intended.

The prototype seeded both from the sum of the id's character codes. That is
deterministic, but it collides constantly — any anagram of an id is the same
book — and it clusters badly, because ids from one instance share a long prefix
and differ in a few digits, so a whole shelf lands in two of the four cloths.

## Decision

**Everything about a placeholder cover is derived from the BookWyrm work id and
nothing else.** `client/src/lib/spine.js` hashes the id with FNV-1a (four lines,
no dependency, well spread over short similar strings) and reads different bit
fields for different properties, so width and colour vary independently rather
than in lockstep:

| Property | Derivation |
|---|---|
| binding cloth | `hash % 4` over four muted book-cloth pairs |
| spine width | `(hash >>> 4) % 4` → 22, 33, 44 or 55 px |
| spine height | `(hash >>> 11) % 5` → 74–94 px inside a 100 px strip |
| gutter, title size | scaled from the cover width, not from the hash |

Never `Math.random`, never an index into the feed, never a counter — those all
look stable within one render and are different on the next one.

A draft book has no work id yet (`bok_kladd` comes off the cover attachment's
name, ADR 0010), so it seeds from the title, which is the only stable thing it
has. The jacket therefore does not jump when the edition lands.

## Consequences

- A book keeps its silhouette and its cloth across sessions, devices, the feed,
  the shelf strip, the filter chips and the book sheet.
- The cloth pairs live in JavaScript rather than in `app.css`. They are generated
  cover *art* — the same kind of value as a BlurHash — and they never appear as
  UI chrome, so they are not design tokens and must not become any.
- **The trap.** `spineOf` and `clothOf` look like presentation helpers, and a
  reasonable-looking refactor is to memoise them per render or to pass an index
  "since we are already mapping". Both quietly reintroduce order dependence.
  The functions take an id and nothing else, and that signature is the guarantee.
- **The accessibility cost, stated plainly.** A 22 px spine is not a 44 px
  target. The hit area is widened into the 9 px gap on each side — never past it,
  so a tap is never ambiguous — which gets the narrowest spine to 31 px. Every
  book on the strip is also reachable through a full-size cover in the feed and
  through the 56 px book row in the post detail, both of which clear 44 px. The
  alternative was fattening every spine to 44 px, which erases the skyline the
  strip exists to draw.
