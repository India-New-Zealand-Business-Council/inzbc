# ADR-0002: Internal platform hosting

- Status: Accepted
- Date: 2026-07-26
- Deciders: Bhanu (tech lead), with INZBC to confirm anything that touches org-owned identity
- Supersedes: nothing. Blocks: database migrations, the site-forms receiver service
- Graduated to option B by [ADR-0004](0004-platform-graduation.md) on 2026-07-27 (trigger 1 met);
  the blocks above are lifted there

## Context

SIP needs somewhere to run. The question has been open since discovery and is recorded as a blocker
in [issue #21](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/21) ("internal
platform decision: Microsoft 365 vs repo-hosted"). It blocks turning `database/schema.sql` and
`schemas/state-machine.md` into migrations, and it blocks the forms receiver service.

ADR-0001 already fixed the stack: Python, FastAPI, Pydantic, Postgres, with OpenAPI to TypeScript
codegen. This decision is about **hosting and operational shape**, not language.

The constraints that actually bind:

- **Scale is small.** One run per day. Five users. Single-digit documents per day. The output is one
  Daily Intelligence Brief reviewed by one person and approved by one person.
- **Budget is near zero.** The repository is private, so GitHub Advanced Security is a paid add-on;
  Actions minutes are finite; there is no cloud spend approved.
- **There is no operations team.** Three part-time engineers, and the CEO simultaneously holds
  analyst, secretariat and system-administrator roles. Nobody owns credential rotation.
- **Turnover is structural.** Whoever sets up bespoke infrastructure will not necessarily be here to
  maintain it.
- **Nothing is user-facing yet.** During the controlled launch the run is manual and distribution is
  a human sending one email.

## Options considered

### A. Microsoft 365 aligned
Entra ID for identity, SharePoint or Azure Blob for storage, Azure Postgres, Microsoft Graph for
mail, Key Vault for configuration, Application Insights for monitoring.

- **For:** INZBC already runs on M365, so identity is organisation-owned and survives any individual
  leaving. It is the conventional answer for a Microsoft-shop client.
- **Against:** real recurring cost against a near-zero budget. Needs tenant administrator consent the
  team does not hold. Each managed service adds a credential-rotation clock with no named owner, so
  the likely failure mode is a silent expiry months later. Adds four IAM surfaces to defend for a
  five-user system.

### B. Repo-hosted, GitHub-native
GitHub Actions to run the job, a free-tier managed Postgres (Supabase or Neon), storage in the
repository or Drive, GitHub accounts for authentication.

- **For:** near-zero cost, the team already lives in these tools, no new identity system, failures are
  visible in the Actions log.
- **Against:** identity is not INZBC-owned. Free tiers have limits and can change. Still means keeping
  a database alive that nothing yet needs.

### C. Process, not service (chosen)
No always-on server. A scheduled or manually triggered job boots, performs one run, writes the brief
and its evidence, and exits. Approval happens through GitHub Issues or pull requests. No database
until something genuinely requires state that outlives a single process.

- **For:** removes hosting, uptime, deployment and most monitoring from the problem entirely. Matches
  the actual scale. The pattern is already proven in this programme: `daily-india-nz-news-agent`
  runs exactly this way today, fetching news, calling a model, writing Sheets and emailing a digest.
  The orchestrator's append-only history plus git already provide audit and versioning.
- **Against:** defers the database. Pre-publish approval screens (Paras's QA and CEO decision UI) need
  somewhere to hold "drafted, awaiting sign-off" between a run and whenever a human next looks. That
  is the real trigger for needing a server, and it is a question of workflow, not of traffic.

## Decision

**Adopt option C: run SIP as a process, not a service**, and record an explicit graduation trigger so
moving to option B is a deliberate decision rather than infrastructure creep.

Concretely, for now:

- The daily run is a scheduled or manually triggered GitHub Actions job invoking the existing
  orchestrator entry point.
- Run evidence is the orchestrator's append-only transition history plus the committed brief; git
  provides versioning and audit.
- Approval and QA are recorded through GitHub (issue or pull request per run), which costs no new
  authentication because every team member already has an account.
- Monitoring is a dead-man's switch: alert if the day's brief has not appeared by 07:05. Five people
  notice a missing brief immediately; a full observability stack would duplicate that.
- No database is provisioned yet. `database/schema.sql` stays the contract both other lanes build
  against.

### Graduation trigger

Move to **option B** when **any** of these becomes true:

1. Pre-publish approval genuinely blocks the run — that is, the QA or CEO screen must hold pending
   state between the job finishing and a human acting.
2. More than one run per day, or runs that cannot complete inside a single job.
3. Cross-run queries are needed that a read of the append-only log cannot answer.
4. Evidence files outgrow what belongs in git.

Option A is revisited only if INZBC funds it and names an owner for identity and credential rotation.
Organisation-owned identity is a genuine advantage, but it is not worth adopting without someone
accountable for keeping it alive.

## Consequences

**Positive.** Nothing to host, deploy or keep patched. No credential-rotation burden beyond the model
provider key already in use. Cost stays at zero. The decision is reversible: the code is plain Python
behind an entry point, so moving it behind a server later is a deployment change, not a rewrite.
ADR-0001's stack is untouched.

**Negative, and the mitigations.**
- The UI lane cannot build a pre-publish approval flow against a live backend yet. Mitigation: build
  against contract fixtures, which is already how issue #57 is scoped; the graduation trigger exists
  precisely for when that stops being enough.
- "Process, not service" is unusual for a client expecting a web application. Mitigation: this ADR is
  the explanation, and the graduation trigger shows it is a staged decision rather than a shortcut.
- Deferring the database defers migration experience. Mitigation: the schema is already written and
  reviewed; migrating it later is a known, bounded task (issue #44).

## References
- [ADR-0001](0001-backend-language.md) — backend language and contract strategy
- `schemas/state-machine.md`, `database/schema.sql` — the contracts this defers rather than changes
- `apps/sip/core/orchestrator.py` — the entry point a scheduled job invokes
- Issue #21 — where this blocker was recorded
- Issue #44 — turning the schema and state machine into migrations, gated on this decision
