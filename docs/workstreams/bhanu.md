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

## Contracts I own (ship first — they unblock Roshan and Paras)
- DB schema + migrations (from the Intelligence Database v1.9 model).
- API contract (OpenAPI) for pipeline + control endpoints.
- Run state machine (Draft to Distributed/Closed) with illegal-transition guards.
- Auth + RBAC roles; append-only audit log; server-side disabled-control flags.
- Webhook contract for Wix to internal.

## Next up
- [ ] Scaffold monorepo folders + CI (lint/typecheck/test) so checks exist to run.
- [ ] DB schema v0.1 + migrations: runs, candidates, daily_intelligence, action_register, watch_lists, source_library, approvals, audit, exceptions.
- [ ] API contract v0.1 (OpenAPI) covering pipeline + control endpoints.
- [ ] Auth + role model (roles from launch-config) + audit-log middleware.
- [ ] SIP run state machine with server-side guards + disabled-control flags.
- [ ] Backup + run-monitoring design (confirm each scheduled run started, finished, produced output).

## Done
- (none yet)

## Blocked / decisions needed
- Internal platform: Microsoft 365 vs repo-hosted service (AIOS foundation decision).
- SIP app hosting + private domain.

## Definition of done
Contracts published and versioned; auth/audit/state/CI green; disabled-control flags enforced
server-side; Roshan and Paras can run their modules against a live schema + API.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
