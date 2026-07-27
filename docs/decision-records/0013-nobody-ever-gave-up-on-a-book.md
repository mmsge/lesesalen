# 0013 — Lesesalen never says a reader gave up on a book

- **Status:** Accepted
- **Date:** 2026-07-27
- **Contributors:** Claude (agent decision — no human input on the technical
  choice; the mobile redesign handoff set the rule and this record fixes where
  it is enforced in the code)
- **Topics:** bookwyrm, activitypub, ui, ethics, data-contract

## Context

An earlier draft of the redesign had a fourth reading status beside "vil lesa",
"byrja på" and "ferdig med":

> Åsta gav opp *Ein lang roman* på side 88

It reads well and it is a lie twice over.

**BookWyrm has no "stopped reading" event.** Its shelves are `to-read`,
`reading` and `read`. There is no shelf, no activity and no field that means a
reader abandoned a book. Nothing in an outbox can tell you that.

The line came from two places in this codebase that make it *look* available.
`_READING_STATUS_FIELD` maps a `stopped-reading` shelf value to `slutta`, and
`_STATUS_PATTERNS` matches the English phrase "gave up on" in generated prose.
The first is a value BookWyrm does not currently produce; the second is prose
matching, which is fragile by design (see the note in `app/enrich.py`) and can
match a sentence somebody wrote about a different book entirely.

And **the page number made it worse**. "på side 88" turns a guess into a record:
it reads like something the reader logged, at a precision nobody supplied.

## Decision

**No surface in Lesesalen states that a person stopped reading a book.**

1. `slutta` and `ukjend` both render the neutral sentence `status.updated` —
   "{who} oppdaterte lesestatusen for {title}". We know the shelf moved. We do
   not know what the reader meant by it, and we do not guess.
2. What we *can* honestly say is what we can see, and we say only that.
   `client/src/lib/stale.js` looks across the reader's own collection, in the
   reader's own browser, for a (person, book) pair whose most recent event is a
   `byrja` reading status more than 90 days old, and emits one derived line:

   > Åsta har ikkje rørt *Ein lang roman* sidan mars
   > ⚠ Rekna ut av Lesesalen

3. **The derivation is labelled as a derivation.** Hatched background, dashed
   dot, and a dashed "Rekna ut av Lesesalen" badge — three signals that this line
   is arithmetic and not an event. It is also not a link and not a tab stop:
   there is no post behind it to open, and no actions, because there is nothing
   to reply to.
4. **A derived line never carries a page number.** `inferQuiet` nulls `posisjon`
   and `posisjonsmodus` on the item it emits, whatever the event it was derived
   from happened to hold.

## Consequences

- The four-status row in the design (`4l`) becomes three real statuses and one
  visibly derived one. That is what the data supports.
- The inference is local, cheap and private: it runs over `feed.items` in the
  browser, fetches nothing and stores nothing.
- **The trap.** `enrich.py` still recognises `slutta`, and it looks unused —
  the obvious tidy-up is to wire it to a "gav opp" string, because there is a
  status constant sitting right there asking for one. Keeping the mapping and
  routing it to the neutral sentence is deliberate: if an instance ever does
  serve `stopped-reading`, we want to know the shelf changed without claiming to
  know why.
- **The other trap.** The derived line is one card kind away from looking like a
  real one. If the hatch, the dashed dot or the badge is dropped as visual noise,
  the app starts asserting something nobody said. All three are in
  `ReadingStatusCard.svelte` under `.status.inferred`, and the badge is repeated
  on the post detail for the same reason.
