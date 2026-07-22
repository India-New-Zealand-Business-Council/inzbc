# Worklog — Paras

Role: public site, member experience, and all UI. Presents data out; reads through the shared API.
Ordered backlog; take the top **Next up** item. Move finished items to **Done**.

## Lanes (my paths)
```
/apps/site/**
/apps/sip/ui/**
/apps/comms/ui/**
/apps/fta/ui/**       (the Explainer's embedded UI; Roshan owns its service)
```
Design: follow `DESIGN.local.md`. Do not invent a look; brand tokens come from INZBC's kit.

## Modules I own (see [docs/modules](../modules/README.md))
[Public website](../modules/website.md) + [Member portal](../modules/member-portal.md) +
[Events & delegations](../modules/events-delegations.md) + [Dashboards](../modules/dashboards.md) +
SIP review/approval UI + Comms Assistant UI + FTA Explainer embed.

## Depends on
The shared API + auth for anything that reads/writes data. Roshan's FTA service for the Explainer UI.

## Next up
- [ ] Build the public site in Wix from `apps/site/content/` (blocked: Wix account access + brand kit).
- [ ] CMS collections + dynamic pages (news, events, sector reports, board, sponsors).
- [ ] Member portal shell (Members Area) + member roles; link out to Member Jungle for membership
      (do NOT rebuild membership — see the AIOS Member Jungle decision).
- [ ] Forms: confirmation email + owner notification + webhook to internal (Bhanu's webhook contract).
- [ ] SIP review/approval/registers UI: brief builder (SIP-186), QA (SIP-188), CEO decision, registers.
- [ ] Executive dashboard (control state, open actions, QA/distribution status).
- [ ] Accessibility pass to WCAG 2.2 AA on every public page.

## Done
- Drafted public-page content in `apps/site/content/` (home, about, events, members, connect) from
  page-specs, executive tone, placeholders for INZBC facts. Ready to drop into Wix.

## Blocked / decisions needed
- Wix account access + Wix MCP connection (to build the site).
- Brand kit from Sunil (logo, colours, fonts, photos).
- Membership platform decision (retain/integrate/replace Member Jungle) — build the portal against the choice.
- Backend contracts are published (schema/API/state); SIP UI can start against them once there is a running API.

## Definition of done
Public site matches the specs and is WCAG 2.2 AA; forms deliver to the right owner; SIP UI lets a
brief be QA'd, approved and packaged for manual send; dashboards read the DB. No pipeline writes.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
