# ADR-0004: Graduate to option B — hosted service, managed Postgres, GitHub identity

- Status: Accepted
- Date: 2026-07-27
- Deciders: Bhanu (tech lead), with INZBC to confirm organisation ownership of the OAuth app and the
  post-capstone owner
- Graduates [ADR-0002](0002-internal-platform.md) from option C to option B. Unblocks: database
  migrations (issue #44), the site-forms receiver service

## Context

ADR-0002 chose option C, "process, not service", and deliberately recorded four graduation triggers
so that moving to option B would be a decision rather than drift. The first of those triggers reads:

> Pre-publish approval genuinely blocks the run — that is, the QA or CEO screen must hold pending
> state between the job finishing and a human acting.

That condition is now met, not anticipated. REQ-U-01 (brief review and QA interface) and REQ-U-02
(CEO decision screen) are both `Must` priority and both require exactly this: a run reaches
`Awaiting CEO Decision` and stays there until a human acts, which may be hours later and in a
different process. A scheduled job that boots, runs and exits cannot hold that state, and the
append-only history in memory dies with the process.

ADR-0002 anticipated this precisely — it listed "the UI lane cannot build a pre-publish approval
flow against a live backend yet" as the known negative, with building against contract fixtures as
the mitigation "until that stops being enough". It has stopped being enough.

Option A (Microsoft 365 / Azure) remains out of scope on ADR-0002's own terms: it is revisited only
if INZBC funds it and names an owner for identity and credential rotation. Neither has happened.

This ADR therefore does two things: it records the graduation, and it decides the operational
questions option B left open. ADR-0002 described option B as "GitHub Actions, a free-tier managed
Postgres, GitHub accounts for authentication" — which does not say where an always-on API runs.
Actions can execute a scheduled job; it cannot serve a React client.

## Decision

Adopt option B, with the following specifics.

### Hosting

| Concern | Decision |
|---|---|
| API (FastAPI) | **Fly.io**, Docker deploy, scale-to-zero permitted |
| Public FTA UI | **Cloudflare Pages** — static, CDN-backed, unauthenticated |
| Staff SIP UI | **Served by the API as static files, same origin** |
| Database | **Neon** free-tier Postgres, pooled connection string |
| TLS + domain | Provider HTTPS on `*.fly.dev` and `*.pages.dev` |

Fly and Neon both appear on the free-tier candidate list already recorded in
`docs/ai-service-architecture.md`, and both keep ADR-0002's near-zero-cost constraint. A custom
domain is `[[to confirm with INZBC]]` and is not on the critical path.

Splitting the two front ends is a security decision, not an aesthetic one. **The authenticated
surface is same-origin**, so session cookies never cross an origin boundary and CORS is not part of
the staff auth path — the place where a CORS mistake is most damaging. CORS is enabled only on the
public FTA read endpoint, which is unauthenticated and carries no cookies.

### Environments

Two deployed environments, **both non-production**. `production_enabled` stays `false` in both;
nothing here changes the launch-approval requirement in `docs/sip/README.md`.

- `staging` — auto-deploys on merge to `main`. Synthetic data only.
- `uat` — promoted manually via `workflow_dispatch`. Used for the client acceptance session.

Neon database branching gives each environment its own branch from one free-tier project.

### Deploy and rollback

Deployment is a GitHub Actions job; no local `fly deploy` from a laptop. Rollback is
`fly releases` to find the prior release, then redeploy that image digest. Every deploy records the
image digest in the job summary so the rollback target is never guessed. Migrations run as a
separate step before the release is promoted, and are expand-then-contract so a rollback of the app
does not require a rollback of the schema.

### Secrets

GitHub Actions secrets for CI, Fly secrets for runtime, Neon connection strings held as Fly secrets.
Never in a file, a commit, an issue or a PR. `.env.example` continues to list names only. This
extends the existing rule in `docs/sip/README.md` rather than replacing it.

### Identity and authorization

GitHub accounts provide **authentication only**. They do not confer authorization.

- **OAuth app ownership.** The OAuth app is owned by the `India-New-Zealand-Business-Council`
  organisation, not by an individual. ADR-0002 rejected option A partly because nobody owned
  identity; registering this app personally would reintroduce exactly that failure.
  `[[INZBC to confirm org-level registration]]`
- **Allowlist, not open sign-in.** A successful GitHub login is matched against a `users` row by
  GitHub login. No active row → `403`, no session issued. An authenticated GitHub user is not an
  authorised INZBC user.
- **Role mapping is data.** `users.role_id` → `roles`, seeded from
  `docs/sip/launch/launch-config.md` (CEO / SIP Owner, Analyst, Quality Reviewer). Changing who
  holds a role is a data change, not a deploy.
- **Server-side sessions, not JWTs.** An opaque session id in a cookie, session state in Postgres.
  Chosen so revocation is immediate: a stateless token cannot be withdrawn before it expires, and
  offboarding has to take effect at once.
- **Cookie flags.** `HttpOnly`, `Secure`, `SameSite=Lax`, host-only — no domain wildcard.
- **CSRF.** A double-submit token on every state-changing request. `SameSite=Lax` alone does not
  cover top-level POST navigation.
- **Expiry.** Absolute 12 hours, idle timeout 60 minutes, whichever comes first.
- **Offboarding.** Set `users.active = false`; sessions fail on their next request. No code change,
  no redeploy, no credential rotation.

Separation of duties stays server-side, as `launch-config.md` already requires: a run's analyst may
not be its reviewer, and the Quality Reviewer keeps independent stop authority.

### Post-capstone ownership

`[[INZBC to name an owner for the deployed services and the OAuth app]]`. **Default if unnamed at
capstone end: the Fly and Neon resources are torn down and the system returns to option C.**
ADR-0002 declined to adopt infrastructure nobody was accountable for; leaving unowned services
running would contradict that for no benefit. This is a deliberate default, not an oversight.

## Consequences

**Positive.** The UI lane is unblocked: REQ-U-01 and REQ-U-02 can be built against a live backend
instead of fixtures. Migrations are unblocked (issue #44). Run state, approvals and audit outlive a
process, which is what makes the append-only audit requirement enforceable rather than aspirational.
Identity costs nothing new — everyone already has a GitHub account. ADR-0001's stack is untouched.

**Negative, and the mitigations.**
- Cost is no longer structurally zero; it is zero only while free tiers hold. Mitigation:
  scale-to-zero on Fly, Neon's free branch limits sit well above a five-user system, and the
  teardown default above bounds the exposure.
- Identity is still not INZBC-owned in the Entra sense. Mitigation: an organisation-owned OAuth app
  plus a database allowlist means access is revocable by INZBC without depending on any individual.
- There is now something to patch, deploy and keep alive — the burden ADR-0002 avoided.
  Mitigation: a container with two dependencies, deploys only via Actions, documented rollback.
- Free-tier providers can change terms. Mitigation: the app is a plain Docker image against plain
  Postgres; moving hosts is a redeploy, not a rewrite.

## References
- [ADR-0002](0002-internal-platform.md) — the decision this graduates, and the trigger it defined
- [ADR-0001](0001-backend-language.md) — the stack this deploys, unchanged
- [ADR-0003](0003-frontend-tooling.md) — the frontend tooling the hosted UI adopts
- `docs/requirements.md` — REQ-U-01, REQ-U-02, the requirements that met the trigger
- `docs/sip/launch/launch-config.md` — the roles seeded into `roles`
- `docs/sip/README.md` — `production_enabled`, secrets handling, security review before staff use
- Issue #44 — migrations, unblocked by this decision
