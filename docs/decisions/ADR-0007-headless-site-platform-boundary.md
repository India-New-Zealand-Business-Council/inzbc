# ADR-0007: Where the website ends and the platform begins

**Status:** Proposed — recommendation from the platform lane, not yet a client decision
**Date:** 2026-08-12
**Decision owner:** Bhanu (platform), with INZBC to confirm anything affecting hosting or cost

## Context

Two things changed independently and now meet.

The website moved to **Wix Vibe** (Astro, React, Tailwind), in the `inzview` repository. Twelve
routes, all returning 200, each with a migrated body. The earlier Wix Studio build is retired to
`legacy/`. The site is currently static: `src/components/inzbc/content.ts` holds the copy and there
is no API client anywhere in the non-legacy tree.

The platform gained authentication (#272, #278, #279, #280). Every business route now requires an
opaque server-side session cookie, a CSRF token on writes, and a named role. `/api/fta` and
`/health` remain public, deliberately.

The intent is to use Wix Vibe as the backend for the site. That is right for the site and wrong for
SIP, and the distinction has not been written down anywhere. This ADR writes it down before someone
wires a staff tool into `inzview` and discovers the problem in a demo.

## The constraint

The session cookie **cannot reach the platform from the site's origin.** Three independent
mechanisms each prevent it, and any one is sufficient:

| Mechanism | Where |
|---|---|
| `allow_credentials=False` | `services/api/hardening.py:176`, commented "public read endpoint; no cookies cross an origin" |
| `SameSite=Lax` | `services/api/session.py`; a browser will not attach the cookie to a cross-site XHR |
| Host-only cookie, no `Domain` attribute | scoped to the API host alone |

None of that is accidental. It is ADR-0004's position and it is correct for a public read endpoint.
The consequence is simply that it also rules out a credentialed call from another origin.

## Decision

**The website and the staff tools are different products with different backends, and the boundary
is the session.**

**1. Wix Vibe is the backend for the website.** CMS, forms, members, media and hosting. It is not
the backend for SIP: FastAPI, Postgres, the model gateway, the redaction gate and the audit trail
live on the platform, per ADR-0001 and ADR-0004.

**2. The public site consumes only public platform endpoints.** Today that is `/api/fta`. It needs
no cookie, so CORS with `allow_credentials=False` is sufficient and nothing has to be relaxed.

**3. Staff tools are served from the platform's own origin.** `apps/sip/ui`, `apps/comms/ui`,
`apps/dashboard/ui` and `apps/member/ui` already exist and already build. Served from the API's
origin the cookie works unchanged: no CORS, no `SameSite` relaxation, no third-party host holding a
credentialed path.

## Options considered

**Serve staff tools from the platform origin.** Chosen. Cheapest, and it is what the code already
assumes. `services/api/main.py` already mounts `static/` at `/` when present.

**One domain, reverse proxy.** `inzbc.org` for the site, `inzbc.org/api` for the platform. The
cookie stays host-only and everything works. Rejected for now on cost and operational surface, not
on merit: it is the better answer if the two ever need to look like one product to a member.

**Relax to `SameSite=None; Secure` with `allow_credentials=True` and an origin allowlist.**
Rejected. It re-opens the cross-site request surface the double-submit token exists to close, and
hands a third-party host a credentialed path into a system holding member data. The gain is
convenience; the cost is the control.

## Consequences

**The site cannot be CI-gated the way the platform is.** `npm install` fails in `inzview` because
`@wix/locale-dataset-javascript` is on Wix's private registry, so there is no local type-check or
build. Verification happens in a browser against the published site. That is a real difference in
assurance between the two halves and should be stated to INZBC rather than discovered at handover.

**"Merged" and "live" are separate events for the site.** Pushing to `main` syncs code into the
Vibe workspace; publishing is a button in the Vibe editor with no API. The platform deploys from
git; the site does not.

**Two writers on one branch.** The Vibe workspace commits generated changes, so pushing while it
holds uncommitted work produces a merge someone resolves by hand. That has already happened once,
committing literal conflict markers into five source files.

**A member-facing logged-in experience is not covered by this ADR.** Membership is on Member
Jungle, the site links out, and no decision here changes that. If INZBC later wants members
authenticated on the site itself, that is a new decision and probably wants the reverse-proxy
option.

## What this does not decide

- Where the platform is hosted at handover. ADR-0004 leaves the managed-Postgres provider and
  region unconfirmed and calls free-tier hosting interim.
- Whether the staff tools are deployed at all during the engagement. #99 is unblocked but not done.
- The Member Jungle integration question, which is still with INZBC.
