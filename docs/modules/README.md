# Module map — INZBC AI Operating System

The full scope, so the repo reflects the whole programme, not just SIP. Every module below is
INZBC-only (WIA, Kiwi Indians, WAIP, personal and political systems are out of scope). Detail and
governance live in the [programme brief](../inzbc-ai-operating-system.md); this is the index.

Legend — Status: `spec` (outline exists) · `launch` (running manually) · `build` (in code) · `planned`.

| # | Module | What it does | Complexity | Owner | Status | Spec |
|---|--------|--------------|------------|-------|--------|------|
| 1 | **Public website** | Marketing + conversion: home, about, board, events, news, sponsors, FTA overview, join pathway | Med — Wix CMS, dynamic pages, forms, SEO, WCAG 2.2 | Paras | planned | [website.md](./website.md) |
| 2 | **Member portal** | Login-gated member resources, renewals, briefings, request forms | High — identity, roles, links to Member Jungle | Paras | planned | [member-portal.md](./member-portal.md) |
| 3 | **Membership / CRM** | Member + organisation records, categories, renewals, corporate seats, consent | High — system-of-record decision (Member Jungle), payments, GST, migration | Bhanu + INZBC | planned | [membership-crm.md](./membership-crm.md) |
| 4 | **Sponsors & trade services** | Sponsor pipeline, benefit delivery, trade-service requests, introductions, delegations | Med-High — pipeline, evidence-of-delivery, confidentiality | Bhanu | planned | [sponsors-trade-services.md](./sponsors-trade-services.md) |
| 5 | **Events & delegations** | Event lifecycle, registration, VIP, check-in, follow-up, delegation itineraries | Med — event platform choice, registration, comms | Paras | planned | [events-delegations.md](./events-delegations.md) |
| 6 | **FTA Implementation Centre** | Sourced FTA knowledge base + the Opportunity Explainer (tariffs, RoO, sector guidance) | High — source governance, citations, effective dates, no unsupported claims | Roshan | spec | [fta-centre.md](./fta-centre.md) |
| 7 | **SIP (Strategic Intelligence Platform)** | Controlled daily intelligence: collect, verify, score, route, review, approve, audit | Very high — RBAC, state machine, audit, fail-closed, human approval | Bhanu core / Roshan pipeline / Paras UI | launch | [../sip/](../sip/) |
| 8 | **AI Communications Assistant** | Staff-only drafting for newsletters, events, posts; adversarially tested | Med-High — controlled prompts, prohibited-data rules, human approval | Roshan/Paras | planned | [comms-assistant.md](./comms-assistant.md) |
| 9 | **Executive & board dashboards** | Read views over the above: control state, actions, QA/distribution, sponsor/member metrics | Med — reporting over the shared DB | Paras | planned | [dashboards.md](./dashboards.md) |

## Cross-cutting (apply to every module)
Not features — the spine. Detail in the programme brief.
- **Identity & roles** — member category vs entitlement vs portal access vs admin authority (brief §7).
- **System-of-record map** — one authoritative store per data type (brief §6).
- **Security** — MFA, least privilege, audit, secrets management, backups (brief §12).
- **Privacy** — PIA before member data / AI use, collection notices, retention, breach process (brief §11).
- **AI governance** — approved workspaces, prohibited inputs, human approval, no auto-publish (brief §13).
- **Accessibility** — WCAG 2.2 AA on every public surface.

## Governance doc set (to create in Phase 1, per brief §20)
These have homes but are not yet written. Each is an INZBC decision input, not code:
`docs/governance/` (decision register, RACI, licence/account register), `docs/privacy/` (PIA,
notices), `docs/security/` (threat model, incident response, backup — backup exists in the
news-agent launch pack), `docs/data/` (system-of-record map, data inventory, retention, migration),
`docs/membership/` (platform options, business rules, member-data map), `docs/testing/`,
`docs/operations/` (runbooks, handover).

## What's actually built vs planned (be honest)
- **Built + merged:** SIP collection agent (draft-only, gated), SIP v0.9 launch pack, backup
  procedure + verify script, all planning/governance docs, team workflow.
- **Running manually:** SIP controlled launch (27–31 Jul), on the workbook + agent.
- **Planned (needs the four foundation decisions + INZBC inputs before build):** modules 1–6, 8, 9,
  and the SIP application that replaces the manual workbook.

Nothing past Phase 0/1 builds until INZBC signs the foundation decisions (brief, Executive decision).
