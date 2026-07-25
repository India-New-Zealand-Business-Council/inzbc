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
- [ ] SIP review/approval UI against contract fixtures (startable now, no live backend): brief
      builder (SIP-186), QA checklist (SIP-188), CEO decision + registers — and enforce the run
      state machine client-side (illegal transitions disabled in the UI, mirroring
      `schemas/state-machine.md`, with the server still the authority).
- [ ] Design system from `DESIGN.local.md`: token-driven component library on placeholder brand
      tokens (one-day swap when Sunil's kit arrives), WCAG 2.2 AA behaviour — focus order,
      contrast, keyboard paths — built into each component rather than audited at the end.
- [ ] FTA Explorer embed UI against Roshan's service contract: query → sourced answer rendering
      (citation, effective date, next step, escalation path when the service returns no match).
- [ ] Comms Assistant review UI: draft view with diff-against-previous and the named-reviewer
      approval gate (nothing publishable without a recorded human approval).
- [ ] Build the public site in Wix from `apps/site/content/` (account access granted at team
      level — can start in the Wix editor now; programmatic build additionally needs the Wix MCP
      connected; still blocked on the brand kit either way. See `docs/discovery.md` OI-1).
- [ ] CMS collection schemas mapped to page-specs now (news, events, sector reports, board,
      sponsors), ready to create as dynamic pages now that Wix account access is in place.
- [ ] Member portal shell (Members Area); link out to Member Jungle for membership
      (do NOT rebuild membership — see the AIOS Member Jungle decision). SHARED-OK: member
      roles/access control moved to Bhanu's worklog — it builds on his auth/RBAC model.
- [ ] Forms UI: confirmation email + owner notification. SHARED-OK: the webhook-to-internal
      delivery (contract + receiver service) moved to Bhanu's worklog.
- [ ] Executive dashboard UI (control state, open actions, QA/distribution status) — reads
      Bhanu's dashboards data-layer endpoints.
- [ ] Final WCAG 2.2 AA audit across every public page (components already carry the behaviour;
      this is the end-to-end verification pass).

## Done
- Drafted public-page content in `apps/site/content/` (home, about, events, members, connect) from
  page-specs, executive tone, placeholders for INZBC facts. Ready to drop into Wix.

## Blocked / decisions needed
- Wix MCP connection, for programmatic build (account access is already granted at team level —
  manual build in the Wix editor can start now; see `docs/discovery.md` OI-1).
- Brand kit from Sunil (logo, colours, fonts, photos).
- Membership platform decision (retain/integrate/replace Member Jungle) — build the portal against the choice.
- Backend contracts are published (schema/API/state); SIP UI can start against them once there is a running API.

## Definition of done
Public site matches the specs and is WCAG 2.2 AA; forms deliver to the right owner; SIP UI lets a
brief be QA'd, approved and packaged for manual send; dashboards read the DB. No pipeline writes.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
