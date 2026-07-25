# 0004 — Cover images are raster-only and re-encoded on ingest

- **Status:** Accepted
- **Date:** 2026-07-25
- **Contributors:** Claude (agent decision — no human input on the technical
  choice)
- **Topics:** security, xss, images, privacy, caching

## Context

Covers are downloaded from remote instances we do not control and then served
from `lesesalen.msge.no`. That crossing is the whole problem: a file that
arrives as untrusted third-party content leaves as **same-origin** content.

A malicious SVG "cover" served from our own origin executes as our own script,
in the origin that holds the reader's token in `localStorage`. `Content-Type`
on the way in is a claim, not a fact, and a file can be a valid image *and*
something else depending on how it is interpreted.

There is a second, quieter reason to hold covers locally: if the browser loaded
them from the origin instance, every reader's IP would be handed to every
instance whose books appear in their feed.

## Decision

- **Raster formats only.** The declared `Content-Type` must be one of
  jpeg/png/webp/gif, *and* the decoded format must be one of JPEG/PNG/WEBP/GIF.
  Both checks, because the first is only a claim.
- **SVG is never stored and never served.** Not as a cover, not "just this once
  for a nicer placeholder".
- **Everything is re-encoded from decoded pixels** to JPEG before it touches
  disk. Nothing of the original file survives — no metadata, no trailing
  payload, no colour-profile exploit, no polyglot.
- **`Content-Type` is pinned on the way out** to `image/jpeg` rather than
  sniffed from the file, and served with `X-Content-Type-Options: nosniff`.
- **Decompression bombs** are capped via `Image.MAX_IMAGE_PIXELS` before Pillow
  decodes anything remote, and the download has a byte cap of its own.
- **Fetched once, at cache time**, not per view. So no reader's IP reaches the
  origin instance, and because the fetch is not tied to a view, this server
  learns nothing about who looked at what.

## Consequences

- Covers that are genuinely SVG are simply absent, and the card falls back to a
  tinted placeholder. Acceptable: BookWyrm covers are photographs of book
  jackets.
- Re-encoding costs a little quality and a little CPU, once per book, ever.
- The stored file is always `<book-id>.jpg`, so the serving path can pin the
  type without inspecting anything.
- The BlurHash is computed from the same decoded image at ingest, which is why
  the placeholder tint is available before the JPEG loads.
