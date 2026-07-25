# 0006 — `require-trusted-types-for 'script'` blanks the app in Chromium

- **Status:** Accepted
- **Date:** 2026-07-25
- **Contributors:** Claude (agent decision — no human input on the technical
  choice; the project brief called this directive "a cheap backstop" and asked
  for it to be verified in Phase 4 rather than assumed, which is exactly what
  surfaced the problem)
- **Topics:** security, csp, svelte, incident, browser

## Context

The security design leans hard on the Content-Security-Policy, because the
reader's token lives in `localStorage` and one successful XSS is a full account
compromise. Adding `require-trusted-types-for 'script'` looks like a free extra
layer: it is Chromium-only, it is cheap, and every hardening checklist suggests
it.

Shipped, it blanks the entire application.

**The symptom:** a white page, an empty `<div id="app">`, and one console error:

```
Refused to ... This document requires 'TrustedHTML' assignment.
TypeError: Failed to set the 'innerHTML' property on 'Element':
This document requires 'TrustedHTML' assignment.
```

**The cause:** Svelte does not build components with `createElement` calls. It
compiles each component's markup to an HTML string and instantiates it by
assigning to `innerHTML` on a `<template>`. Enforcing Trusted Types forbids
exactly that assignment, so *nothing* renders — the failure is total, not
partial.

**Why it is a trap worth recording:** it fails in Chromium only. Firefox and
Safari do not implement Trusted Types enforcement, so a developer testing there
sees a perfectly working app. And the directive reads as pure upside on review.

A default Trusted Types policy does not rescue it either. Such a policy would
have to pass Svelte's own compiled templates through untouched — including the
HTML comment anchors Svelte relies on for reactivity, which every sanitiser
strips by default — while still sanitising genuine remote content. A policy
permissive enough for the former is not doing the job of the latter, and a
policy strict enough for the latter breaks rendering.

## Decision

**`require-trusted-types-for 'script'` is not in the CSP.** The rest of the
policy is unchanged and remains strict:

```
default-src 'none'; script-src 'self'; style-src 'self';
img-src 'self' https: data:; font-src 'self'; connect-src 'self' https:;
manifest-src 'self'; base-uri 'none'; form-action 'none';
frame-ancestors 'none'; object-src 'none'; upgrade-insecure-requests
```

`script-src 'self'` and `object-src 'none'` are the directives that actually
stop an XSS, and neither is weakened. The defence Trusted Types would have
duplicated is provided explicitly instead: **every** path from remote HTML to
the DOM goes through DOMPurify with an allowlist
(`client/src/lib/sanitise.js`), and `RichText.svelte` is the only component in
the app permitted to use `{@html}`.

A regression test (`test_csp_does_not_enforce_trusted_types`) and a CI assertion
both fail if the directive comes back, because the alternative is discovering it
from a user reporting a blank page in Chrome.

## Consequences

- No Trusted Types backstop against a future `innerHTML` introduced by a careless
  refactor. Mitigated by the single-component `{@html}` rule, the DOMPurify
  allowlist, and server-side sanitising with `nh3` on everything `/api/berik`
  returns.
- If Svelte ever grows Trusted Types support, this is worth revisiting — with a
  new record, and with a Chromium check before merging.
- **Verified empirically**, not reasoned about: the app is loaded in headless
  Chromium and asserted to produce zero CSP violations and zero page errors.
  Also verified in the same pass, and worth knowing: Svelte's `style:` directives
  are applied through the CSSOM at runtime rather than as parsed `style`
  attributes, so `style-src 'self'` needs **no** `style-src-attr 'unsafe-inline'`
  exception. The brief left that open; the answer is that it is not needed.
