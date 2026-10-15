# Worklog — Bhanu

Role: foundation, security, integration. Owns the shared contracts the others build against.
Ordered backlog; take the top **Next up** item unless client priorities say otherwise, and note
why if you skip one. Move finished items to **Done**.

## Lanes (my paths — others don't edit without SHARED-OK)
```
/services/api/**
/database/**
/schemas/**
/apps/sip/core/**
/deployment/**
/.github/**   (CI, CODEOWNERS)
```

## Modules I own (see [docs/modules](../modules/README.md))
Foundation + shared services + [Membership/CRM](../modules/membership-crm.md) (decision-gated) +
[Sponsors & trade services](../modules/sponsors-trade-services.md) + dashboards data layer + SIP core.
Modules 3–4 build only after the four foundation decisions; foundation work is unblocked now.

## Contracts I own (ship first — they unblock Roshan and Paras)
- DB schema + migrations (from the Intelligence Database v1.9 model).
- API contract (OpenAPI) for pipeline + control endpoints.
- Run state machine (Draft to Distributed/Closed) with illegal-transition guards.
- Auth + RBAC roles; append-only audit log; server-side disabled-control flags.
- Webhook contract for Wix to internal.

## AI full-stack (strongest first)
These are the flagship AI engineering builds; each is tracked as a GitHub issue on the SIP Platform project board.
- [ ] [ai] Agentic SIP-184 daily-run orchestrator: LLM tool-use loop that drives the run state
      machine, with every irreversible step behind a hard human gate and every fail-closed control
      enforced in code, not by the model. Deterministic replay from the audit log. (#62)
- [ ] [ai] Vector store + embeddings service (pgvector) through the gateway: nearest-neighbour
      retrieval with score thresholds and metadata filters, powering FTA ranking and semantic
      dedupe. (#63)
- [ ] [ai] LLM-as-judge evaluation pipeline: score briefs against a SIP-188/SIP-050 rubric, golden
      set + regression gating in CI, injection-hardened; advises QA, never replaces the human
      gate. (#64)
- [ ] [ai] Streaming Comms Assistant API (SSE): server-side token streaming through the gateway
      with redaction ahead of the call and the named-reviewer gate before any publish. (#65)

## Current delivery — 16 October 2026

Base: main @ `19bb552`. The current owner request is to finish independently deliverable
existing issues and distinguish client decisions from engineering work.

- #36: provider selection, usage/cost metadata and audit persistence merged in PR #420; all CI passed.
- #38: 20 synthetic scoring replay fixtures and 28 regression tests merged, including prompt
  drift and the verification gate. No live semantic scoring result is claimed.
- #135: existing 10 September demo recording verified and screenshots extracted; evidence indexed
  in [demo-evidence.md](../demo-evidence.md). Historical evidence, not production acceptance.

## Next up

- #62: tool-use loop over the existing fail-closed run engine. The transition engine and replay
  already exist; they do not by themselves complete the agent loop.
- #63: shared embeddings/pgvector retrieval capability. No replacement for the production FTA
  ranker is authorized merely by adding this capability.
- #64: advisory quality evaluation and golden-set regression; never an approval gate replacement.
- #45: confirm the approved forms contract, then the internal receiver; shared implementation only,
  not live Wix writes or publication.

## Client-dependent or approval-gated

- #303: verbal residual-risk acceptance reported; required written acceptance not yet supplied.
- #65: streaming remains engineering work; it cannot be represented as closing the prose risk.
- #39: real candidate calibration requires the live backend, captured candidates and configuration.
- #40: technical review approval reported by phone; its written residual-risk condition remains.
- #46 and #201: internal builds not planned; Member Jungle stays authoritative with a link-out.
- #99: INZBC-owned account reported ready and testing/deployment preparation approved. No Render
  service exists yet. Controlled production launch is not authorized.
- #97 and #192: ownership/OAuth registration and platform choice settled. See the
  [16 October decision update](../meetings/client/2026-10-16-decision-update.md).
- #133/#134: session and written acceptance reported complete; source location still needed.
- #189: production launch approval remains outstanding.
- #291: handover recipient and recorded sponsor session remain client dependencies.

Previously stale next-up entries have been reconciled: redaction (#37), auth/audit (#42),
migrations (#44), dashboard endpoints (#47), backup/monitoring design (#48) and secrets-policy
work (#115) are already closed. This does not imply live credentials, a tested production restore
or client sign-off exist. Migrations use `scripts/migrate.py`, not the abandoned Alembic wording.

## Done
- Model gateway v0.1 (`services/api/model_gateway.py`): single server-side model-call path,
  env-configured (no keys in code), retry + fail-closed `GatewayNotConfiguredError`, injectable
  client for tests. Runs on the same OpenAI account/model (`gpt-4.1-mini`) the
  daily-india-nz-news-agent already uses — no new API procurement needed.
- SIP-050 scoring engine v0.1 (`apps/sip/core/scoring.py`): candidate → validated
  `ScoringRecommendation` (relevance 0..5, signal, confidence, reason) via the gateway; strict
  JSON contract, `ScoringParseError` fail-closed on any deviation; `to_assessment()` feeds the
  existing `apply_candidate_assessment` PATCH path and never sets verification (model
  recommends, human decides; verification stays evidence/human-owned).
- Monorepo scaffold + per-lane READMEs; CI already in place (lint/gitleaks/actionlint/links).
- DB schema v0.1 (`database/schema.sql`) grounded in Intelligence Database v1.9.
- API contract v0.1 (`schemas/api-contract.md`) covering pipeline + control endpoints.
- Run state machine v0.1 (`schemas/state-machine.md`) with allowed/illegal transitions.

## Blocked / decisions needed
- SIP app private domain. (Hosting itself is settled — [ADR-0004](../decisions/0004-platform-graduation.md)
  picks Fly.io for the API and Cloudflare Pages for the public UI on provider-issued HTTPS; a custom
  domain is still owed by INZBC and is not on the critical path.)
- Ownership and organisation OAuth registration are settled as recorded above. Deployment and
  credential handover still require verification; no credentials belong in the repository.

## Definition of done
Contracts published and versioned; auth/audit/state/CI green; disabled-control flags enforced
server-side; Roshan and Paras can run their modules against a live schema + API.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
