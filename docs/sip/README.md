# SIP — INZBC Strategic Intelligence Platform

The full build of the confirmed **Trade Intelligence Digest** module. Executive intelligence +
institutional-memory app. NOT a news page, NOT a Wix build.

## Placement decision (why this is not in Wix)
The spec mandates Postgres, server-side model calls, background workers, MFA, immutable audit,
and "the browser must never contain model/DB/source keys." Wix (site builder) cannot host that.

- **SIP app** → separate secure service in code (own host, own DB). This is the Option B service
  from [../ai-service-architecture.md](../ai-service-architecture.md).
- **Wix** → public marketing site only, plus:
  - a public feed page for **Approved Public** items (`/intelligence/public`), and
  - a login link out to the SIP app for staff.
  Spec §15: keep public publishing isolated from the internal platform.

## Non-negotiables (from the spec — do not soften)
- `production_enabled` defaults **false**. No automated runs, no distribution, no public publish
  until a formal launch approval record exists.
- All collection, scoring, model calls, routing → **server-side only**.
- Strict 24-hour **Pacific/Auckland** freshness window.
- High/Critical items require official or two-independent-source verification.
- Human approval gates: Internal / Member / Public are separate states. Model recommends, human
  decides. (Matches the named-reviewer requirement, OI-5.)
- Immutable approval, version, and audit history. Approved records are never edited in place.
- Redaction layer before any external model call (member/Board/confidential data out).

Security-heavy (MFA, auth, audit, secrets, external LLM). Build gets `/codex:adversarial-review`
before any staff use — same gate already required for the AI Comms Assistant.

## Control boundary (current SIP approval state — do not promote drafts)
- **Approved/controlling:** SIP-050 Prompt v1.0, Intelligence DB v1.7, SIP-171 Tracker v3.0,
  SIP-182 v1.0, SIP-183 v1.0, Pilot Runs 1–10.
- **Review drafts only (not controlling):** SIP-183A v0.9, Intelligence DB v1.8, Tracker v3.1.

## Files in this folder
- `SIP_Reference_Config.json` — machine-readable defaults (production disabled, weights, states).
- **TODO:** add the full `SIP_Website_Agent_Implementation_Spec.md` and
  `SIP_Agent_System_Prompt_v1.0.txt` here verbatim (paste the canonical copies to avoid drift).

## Build order (does not start in Wix)
Phase 1 (per spec §13): auth + roles, DB schema, source registry, manual run, raw capture,
assessment+scoring, Daily Brief review, Action Register, doc/version control, audit log,
global production-disabled control. Automation/crawler/public publish behind feature flags after.

Blocked on the same items as the rest of the AI layer: a host (free-tier decision), Claude API
access (Sunil), and the account/auth setup. None of it is a Wix task.
