# Worklog — Bhanu

Role: foundation, security, integration. Owns the shared contracts the others build against.
Ordered backlog; take the top **Next up** item. Move finished items to **Done**.

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

## Next up
- [ ] Turn the state-machine + schema drafts into migrations once the internal-platform decision is made.
- [ ] Auth + role model (roles from launch-config) + audit-log middleware.
- [ ] Webhook contract for Wix to internal.
- [ ] Backup + run-monitoring design (confirm each scheduled run started, finished, produced output).

## Done
- Monorepo scaffold + per-lane READMEs; CI already in place (lint/gitleaks/actionlint/links).
- DB schema v0.1 (`database/schema.sql`) grounded in Intelligence Database v1.9.
- API contract v0.1 (`schemas/api-contract.md`) covering pipeline + control endpoints.
- Run state machine v0.1 (`schemas/state-machine.md`) with allowed/illegal transitions.

## Blocked / decisions needed
- Internal platform: Microsoft 365 vs repo-hosted service (AIOS foundation decision).
- SIP app hosting + private domain.

## Definition of done
Contracts published and versioned; auth/audit/state/CI green; disabled-control flags enforced
server-side; Roshan and Paras can run their modules against a live schema + API.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
