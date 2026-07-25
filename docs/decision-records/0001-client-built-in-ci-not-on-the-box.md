# 0001 — The Svelte client is built in CI and committed, never on the box

- **Status:** Accepted
- **Date:** 2026-07-25
- **Contributors:** Claude (agent decision — no human input on the technical
  choice; the project brief flagged this as "worth an ADR, because it is exactly
  the kind of thing that gets re-litigated", and named the two candidate
  approaches without picking one)
- **Topics:** deploy, docker, ci, build, node, svelte

## Context

Lesesalen has a real front-end build: Svelte components compiled by Vite into a
hashed bundle. The box conventions say two things that together rule out the
obvious approach:

- **no heavy builds on the box** — it is a CAX11 with 3.7 GB of RAM running
  ~22 containers, and memory pressure there does not degrade gracefully, it
  thrashes until SSH dies;
- **no Node outside containers** — so a build step in `make deploy` would have
  to run inside a container anyway.

Meanwhile `make deploy` on every service is `docker compose up -d --build`, and
the box has no image registry. So a multi-stage Dockerfile with a `node:22`
build stage would put `npm ci` + `vite build` on the box on every deploy: a
few hundred megabytes of `node_modules` and a CPU-bound compile, on the box we
are explicitly told not to build heavily on.

## Decision

**The client is built in CI (and by `make client` locally) and the output is
committed to `client/dist`. The box only ever copies it into the image.**

- `client/dist` is deliberately **not** gitignored. `client/node_modules` is.
- The `Dockerfile` has a single Python stage and a plain `COPY client/dist`.
  There is no Node in the image at all.
- CI rebuilds the client from source and **diffs it against the committed
  `dist`**, failing on any difference. Committing build output is only safe if
  a stale bundle is caught mechanically, so that check is what makes this
  decision workable rather than a trap.
- If `client/dist` is missing the app still boots and serves the API; only the
  UI is gone. A broken client build cannot take the service down.

Alternatives considered:

- **Multi-stage build on the box.** Rejected: it is precisely the heavy build
  the box conventions forbid, and it makes every deploy slower and riskier.
- **Push an image to a registry the box pulls.** Genuinely better in the
  abstract, and the right answer if this box ever grows a registry. Rejected
  for now because no other service does it: it would make lesesalen the only
  service whose deploy path differs from `git pull && docker compose up -d
  --build`, and a lone snowflake deploy is its own maintenance cost.

## Consequences

- Diffs contain bundle churn whenever the client changes. Reviewers should read
  `client/src`, not `client/dist`.
- Anyone editing `client/src` must run `make client` and commit the result. CI
  says so explicitly when they forget.
- The committed bundle's reproducibility depends on the pinned Node version in
  CI and on `package-lock.json`. If a Vite or Svelte upgrade changes output for
  identical input, the diff check will fail loudly on the first PR after the
  upgrade — that is the correct place to notice it, but it means the fix is
  "rebuild and commit", not "the check is broken".
- Moving to a registry later is a contained change: delete the committed `dist`,
  restore a build stage, and point `make deploy` at a pull.
