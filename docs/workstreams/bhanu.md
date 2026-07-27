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

## Next up
- [ ] [platform] Model gateway v0.2: token/cost logging + audit-log persistence on top of the
      shipped v0.1 (see Done); wire Perplexity as a second provider behind the same interface.
- [ ] [security] Redaction layer ahead of every external model call (member/Board/confidential
      data stripped) — SIP non-negotiable, currently unowned.
- [ ] [ai] SIP-050 scoring v0.2: run the shipped v0.1 engine (see Done) against real captured
      candidates once repo secrets land; calibrate the prompt against SIP-050's pilot-run
      expectations; add batch scoring to the ingest flow. (SHARED-OK: from Roshan's backlog.)
- [ ] [ai] Eval harness for SIP-050: golden article set + regression checks so prompt changes
      are measured before they ship; include prompt-injection cases (article text is untrusted
      model input); wire into CI.
- [ ] [security] SIP adversarial security review before any staff use (threat model, authz
      matrix, audit coverage) — required by docs/sip/README.md, currently unowned.
- [ ] [security] Secrets management: org-repo secrets for the collection engine + rotation
      policy (clears Roshan's end-to-end run blocker).
- [ ] [security] Auth + role model (roles from launch-config) + audit-log middleware.
- [ ] [platform] Turn the state-machine + schema drafts into Alembic migrations. Unblocked:
      ADR-0002 is Accepted and ADR-0004 graduated it to option B, so a database is now in scope.
      Alembic owns initialisation — do not execute `schema.sql` against the database directly, or
      the schema ends up with two executable sources of truth.
- [ ] [platform] Webhook contract for Wix to internal, plus the internal receiver service for
      site forms. (SHARED-OK: receiver side from Paras; he keeps the form UI + notifications.)
- [ ] [security] Member portal access control: member roles + Members Area gating on the
      auth/RBAC model. (SHARED-OK: from Paras; he keeps the portal shell/UI.)
- [ ] [platform] Dashboards data layer: read endpoints for the executive dashboard (Paras
      builds the UI against them).
- [ ] [platform] Backup + run-monitoring design (confirm each scheduled run started, finished, produced output).

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
- INZBC to register the GitHub OAuth app at organisation level, and to name the post-capstone owner
  of the deployed services (ADR-0004). Unnamed at capstone end means the resources are torn down.

## Definition of done
Contracts published and versioned; auth/audit/state/CI green; disabled-control flags enforced
server-side; Roshan and Paras can run their modules against a live schema + API.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
