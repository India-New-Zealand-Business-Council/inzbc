# API integration specification

How frontend surfaces connect to the shared API (`services/api`): authentication, SIP API calls,
the Trade Digest approval mechanism, and the Comms Assistant request/response flow. This spec
distinguishes what's **built and live today**, what's **specified but not yet built**, and what's
**proposed** — those are three different confidence levels and this doc doesn't blur them.

## Sources
- `services/api/main.py` — the actual FastAPI app, today (one business endpoint plus `GET /health`).
- `services/api/model_gateway.py` — the actual model-call gateway, today.
- `schemas/api-contract.md` — SIP pipeline/control endpoint shapes, v0.1 draft.
- [ADR-0004](decisions/0004-platform-graduation.md) — hosting, identity, session/auth design.
- `docs/ai-service-architecture.md` — how the three AI modules integrate with the site.
- `docs/modules/comms-assistant.md`, `docs/page-specs.md` §6 — Comms Assistant and Digest specifics.
- `docs/workstreams/bhanu.md` — issue #65 (streaming Comms API), redaction layer status.
- `docs/requirements.md` REQ-U-04 — the one integration with a shipped, tested client today.

## Three surfaces, not one API

This is the first thing to get right, because "the shared API" means different things depending
on which frontend is asking:

| Surface | Auth | Origin | Status |
|---|---|---|---|
| Public FTA Explainer (`GET /api/fta/query`) | None — unauthenticated | Same-origin; **no CORS configured** | **Live today** (`services/api/main.py`) |
| Staff SIP control UI | GitHub OAuth + session | Same-origin (API serves the static UI) | Specified (`api-contract.md`), not yet backed by a live DB |
| Staff Comms Assistant UI | GitHub OAuth + session | Same-origin | Architecture decided, endpoint not built (issue #65) |

The **member portal is not on this list.** It is expected to run behind a Wix gate and talk to Member
Jungle, not to `services/api` — see `docs/modules/member-portal-spec.md`. Nothing in this doc
applies to it.

## Authentication flow (staff surfaces only)

Sourced entirely from [ADR-0004](decisions/0004-platform-graduation.md)'s "Identity and
authorization" section — reproduced here as a flow, not re-decided:

1. User clicks "Sign in" → redirected to GitHub OAuth (app owned by the
   `India-New-Zealand-Business-Council` organisation, `[[INZBC to confirm org-level
   registration]]`).
2. GitHub authenticates the user and redirects back with a successful login.
3. **Allowlist check:** the API looks up the GitHub login against the `users` table. No active
   row → `403`, no session issued. **A successful GitHub login is not, by itself, authorisation.**
4. If allowed: `user_roles` resolves the roles the person holds (`SIP Owner` / `Analyst` /
   `Quality Reviewer` / `Secretariat` / `Administrator` / `Board Viewer` / `Auditor`), seeded from
   `docs/sip/launch/launch-config.md`. Role changes are a data edit, not a deploy.

   ADR-0005 replaced the single `users.role_id` column with `user_roles`, so a principal may hold
   several roles at once. That is the normal case here, not an edge one: the three-engineer split
   is a 16-week placement and the steady state afterwards is one person holding every role.
   Authorisation therefore binds to the role used for a given act, not to the person, and any
   code that assumes one role per user is wrong. Not every role in that list is seeded by
   `launch-config.md` today.
5. **Server-side session created** — opaque session id in a cookie, session state in Postgres.
   Not a JWT: chosen specifically so a session can be revoked immediately rather than waiting out
   a token's expiry.
6. **Cookie:** `HttpOnly`, `Secure`, `SameSite=Lax`, host-only (no domain wildcard).
7. **CSRF:** a double-submit token required on every state-changing (non-GET) request —
   `SameSite=Lax` alone doesn't cover top-level POST navigation.
8. **Expiry:** absolute 12 hours, idle timeout 60 minutes, whichever is sooner.
9. **Offboarding:** set `users.active = false`. The next request on any existing session for that
   user fails — no code change, no redeploy, no key rotation needed.

**Separation of duties is enforced server-side, not just in the UI:** a run's `analyst_id` cannot
equal its `reviewer_id` (`api-contract.md`, `schema.sql`). The SIP UI screens in
`docs/sip-ui-spec.md` disable the illegal path in the interface, but the check that actually
matters lives here.

**Status:** this design is Accepted (ADR-0004) but the database migrations that would make
`users`/`roles`/sessions real are still on Bhanu's Next Up list, not Done — so this flow is
specified, not yet live. Build against contract fixtures until that lands, per the same worklog.

## SIP API calls

Full endpoint list from `schemas/api-contract.md` (v0.1 draft — shapes may still move):

**Pipeline (Roshan — data in):** `POST /api/runs`, `GET /api/runs[/:id]`,
`POST /api/runs/:id/{start,pause,resume,complete}`, `GET /api/runs/:id/source-checks`,
`POST /api/runs/:id/source-checks`, `GET /api/source-library`, `GET /api/candidates?run=:id`,
`POST /api/candidates`, `PATCH /api/candidates/:id`,
`POST /api/candidates/:id/{verify,score,route,merge}`.

**Control (Paras — data out + human gates):** `POST /api/reports/daily`,
`GET /api/reports/:id`, `POST /api/reports/:id/qa`, `POST /api/reports/:id/submit`,
`POST /api/reports/:id/{approve,request-changes}`, `POST /api/reports/:id/decision`,
`GET /api/registers/:name`, `POST /api/registers/:name`, `GET /api/dashboard`.

**Cross-cutting:** `GET /api/audit` (append-only, read; **built as
`GET /api/runs/{run_id}/audit`**, scoped to one run with keyset pagination, because an unscoped
read of an append-only table grows without bound and the question people actually ask is what
happened on a given run), `GET /api/config` (server-side flags,
read).

> **Superseded, 31 July 2026.** The control list above is the v0.1 contract. ADR-0005 replaced it
> and `schemas/api-contract.md` now carries the current shape: `/approve` and `/request-changes` for
> the report-approval stream, `/ruling` for the CEO decision, `/distribution` for the authority, and
> `/delivery` for an actual send. Each is a separate command with its own actor and timestamp,
> because a single submission is one action however many rows it writes. Build against
> `api-contract.md`, not the list above.

These endpoints map directly onto the four screens in `docs/sip-ui-spec.md` (brief builder → QA
→ CEO decision → distribution status) — that doc has the screen-by-screen call sequence; this
section is the reference list, not a duplicate walkthrough.

**Fail-closed, every write:** a Critical condition (missing run authority, unapproved version,
missing mandatory source outcome, unverified Critical claim, tracker/DB contradiction, missing
approval, unauthorised distribution) returns an error, never a warning — `api-contract.md`'s own
rule, unchanged here.

**What's actually running today:** none of the above. `services/api/main.py` implements only the
FTA Explainer read path (`GET /api/fta/query`) — its own docstring says the SIP endpoints "land
once the database and the orchestrator's persistence exist." That's the same migrations blocker
noted under Authentication above.

## Trade Digest approval — not an API endpoint today

Worth stating precisely, because the natural assumption (an approval endpoint mirroring the SIP
pattern) is not what's actually specified anywhere:

Per `docs/ai-service-architecture.md` and `docs/page-specs.md` §6, the Digest's human-review gate
is a **Wix CMS status field**, not an API call:

1. The digest pipeline (a separate scheduled service, not `services/api`) evaluates sources,
   summarises, and writes a **draft** directly into a Wix CMS collection via the Wix Data API,
   with `status = draft`.
2. A **named human reviewer** (still unassigned — `docs/discovery.md` OI-5) edits/approves
   **inside the Wix dashboard itself**, flipping the CMS field to `status = published`.
3. The public Digest page and archive render **only** items where `status = published` — this is
   the enforcement point, not a separate approval endpoint.

**So: there is no `/api/digest/*` approval surface to document, because the design deliberately
routes the human gate through Wix's own CMS editing UI instead of a custom one.** If the team
later wants a dedicated approval screen (mirroring the SIP QA/CEO decision pattern in
`sip-ui-spec.md`, e.g. `POST /api/digest/:id/approve`), that would be a **new design decision**,
not something already specified — flagged in Open items below, not built here as if it were.

## Comms Assistant request/response flow

**What's actually built today:** `services/api/model_gateway.py` — a single server-side
`ModelGateway.complete(prompt) -> GatewayResult` path. Provider is OpenAI `gpt-4.1-mini` (the
same account/model `daily-india-nz-news-agent` already uses), fails closed with
`GatewayNotConfiguredError` if no API key is present rather than fabricating a response, one
retry on a transient failure. SIP scoring already calls through this same gateway — the Comms
Assistant is designed to reuse it, not build a second model-call path (`model_gateway.py`'s own
docstring: "SIP scoring, the Comms Assistant and the FTA layer call through here rather than
constructing their own clients").

**What's specified but not built** (`docs/workstreams/bhanu.md` issue #65, "Streaming Comms
Assistant API (SSE)"):

```
Staff user (authenticated, same-origin)
  → submits a drafting request (channel: email | website | social; context/prompt)
  → [BOUNDARY REFUSAL — the call declares a PromptSource; a member record, CRM note,
     Board paper or private message is refused outright. Structured records are built
     through minimise(), which keeps only allowlisted fields]
  → [REDACTION — masks formatted identifiers. It does NOT strip a name, job title or
     employer in prose, and no set of regexes will]
  → ModelGateway.complete() (or a streaming equivalent)
  → SSE token stream back to the UI as the draft generates
  → draft rendered in the UI — never sent, never published
  → named human reviewer edits/approves (docs/modules/comms-assistant.md "Definition of done")
    [API built: POST /api/comms/drafts/{id}/approve records who approved, when, and refuses the
    draft's own author (BR8). The review UI that calls it (#60) is not built yet — this is the
    endpoint it will call, not the reviewer's screen.]
  → only on approval: handoff to the actual send/publish channel (mechanism not specified —
    see Open items)
```

**A gap worth flagging prominently, not softening.** Both controls above are built and enforced on
every call: `POST /api/comms/draft` exists at `services/api/comms.py` and goes through
`ModelGateway.complete()`, which refuses a prohibited source and then redacts. That closes the
structured case.

**It does not close the prose case, and this is the live gap.** The Comms brief is free text a
staff member types, so there is no record to minimise and nothing can tell a member's name from any
other words. The call declares `STAFF_AUTHORED`, which records where the text came from and not
that it is clean, so an operator who pastes

    Board minutes: Priya Sharma, Chief Executive at Koru Exports, opposed the offer.

into a brief sends exactly that. It satisfies `check_source`, survives redaction untouched, and
violates ADR-0006 §1 and §3 while every automated control reports success.

What bounds it today is the operator being told not to, in `operator-guide.md` §3. That is a
procedure, not a boundary, and `comms-assistant.md`'s "Prohibited by default: no
member/sponsor/stakeholder personal data... no confidential government/commercial data" asks for a
boundary. Tracked as #303.

**The request shape changed, and the gap did not close.** As of #303 the endpoint takes
`{content_type, topic, key_points[], links[], tone}` instead of `{content_type, brief}` — a
200-character topic, up to eight 300-character key points, up to five URLs, and a controlled tone.
Callers must send the new shape; `extra="forbid"` means the old body is rejected outright rather
than silently ignored.

The declaration to the gateway is still `STAFF_AUTHORED`, deliberately. Routing named fields
through `minimise()` and declaring `MINIMISED_RECORD` was considered and rejected as untrue:
`minimise()` drops fields nobody named, it does not clean what a human typed into a field that was
named. The exposure is smaller and the same in kind.

Response shapes are unchanged. The brief is rendered to text before storage, so `DraftOut`,
`CommsDraftOut` and every read path are unaffected.

**Also not yet true:** the adversarial/security review `comms-assistant.md` requires "before
staff use" hasn't happened (nothing built yet to review) — this flow cannot ship to real staff
use before that review passes, same gate as SIP.

## Cross-cutting rules (every surface)

- **No secrets, no model calls, from the browser** — every model call goes through
  `model_gateway.py` server-side (NFR-01, shipped, tested — `test_model_gateway.py`).
- **Fail-closed on Critical conditions** (NFR-02) — across SIP gates today; the same principle
  should extend to the Comms redaction gate once it's built, per the flag above.
- **Same-origin for the authenticated surface** — deliberate per ADR-0004: "session cookies never
  cross an origin boundary and CORS is not part of the staff auth path."
- **Single-origin today, including the public endpoint, but that is not ADR-0004's design.**
  ADR-0004 puts the public FTA UI on a separate host with CORS enabled on the read endpoint. The
  current deployment serves both from one origin because the authenticated surface does not exist
  yet, which `Dockerfile:3-7` states as an interim decision: with no cookies and no member data,
  removing CORS entirely is safer than configuring it. `services/api` installs no CORS middleware.
  When the staff surface lands, ADR-0004's split applies and CORS returns on the public endpoint
  only.
- **`production_enabled` stays false** everywhere until a formal launch-approval record exists
  (`docs/sip/README.md`). To be exact about what that means today: the API has no SIP write
  endpoints, no auth, no RBAC, no audit middleware and no distribution path, so there is nothing
  for the flag to gate yet. It is a required future control, and the same gate should cover any
  Comms send or publish handoff.

## Open items
1. Migrations (issue #44) are the real blocker for every SIP endpoint above going live — build UI
   against contract fixtures until then, per `docs/workstreams/bhanu.md`.
2. Redaction layer for the Comms Assistant: unowned. Needs an owner before any real request flow
   is built, not just before launch.
3. SSE streaming Comms endpoint (#65): not built. `model_gateway.complete()` is synchronous,
   single-response today — streaming is new work, not a small extension.
4. Comms Assistant send/publish handoff mechanism after human approval: not specified anywhere
   (email? Mailchimp? manual copy-paste by staff?) — `docs/ai-service-architecture.md`'s own Open
   Questions asks this exact thing (#4) and it's still open.
5. Whether the Trade Digest should ever get a dedicated approval API (vs. staying a Wix CMS status
   flip) is an open design question, not a decision — don't build one without confirming the team
   wants to move off the CMS-gate design.
6. Named human reviewer for Digest/Comms output (OI-5) is still unassigned — blocks real use of
   either flow regardless of what's technically built.
