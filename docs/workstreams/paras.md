# Worklog — Paras

Role: public site, member experience, and all UI. Presents data out; reads through the shared API.
Ordered backlog; take the top **Next up** item unless client priorities say otherwise, and note
why if you skip one. Move finished items to **Done**.

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
      Local implementation landed in #85–#87/#89/#91; what remains is the deployed website
      integration, which is what REQ-U-04 actually asks for.
- [ ] Playwright E2E for the FTA slice (task 1.2). Three cases, the third specifically:
      1. query → sourced answer, with citation, effective date and confidence rendered;
      2. query → no-match, asserting the Action Required escalation renders and no citation
         appears anywhere;
      3. **320px reflow (WCAG 2.2 §1.4.10)** — open at 320px width, submit a query, assert
         `document.documentElement.scrollWidth <= clientWidth` (no horizontal scrolling), and
         assert the input, submit button, answer cards and citation text all stay visible and
         usable. The CSS fix landed in #91 and was verified by a one-off Chromium measurement;
         until this test exists, that behaviour is **not** guarded by CI.
- [ ] Comms Assistant review UI (#60): draft view with diff-against-previous and the
      named-reviewer approval gate (nothing publishable without a recorded human approval).
      Blocked on the service side (#53). **Not the same screen as the drafting UI below** —
      #60's scope is reviewing/approving a draft already produced, not producing one.
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
- Comms Assistant drafting UI (`apps/comms/ui`): content-type selector, brief input,
  generate/loading/error states, output display, copy-to-clipboard, clear/reset. Taken out of
  backlog order — not the top **Next up** item (SIP review/approval UI) — because it was the
  task at hand; no open issue tracked this exact scope, so the PR refs #60 (the closest existing
  Comms Assistant UI issue) as preliminary work, not a claim of closing it. `POST
  /api/comms/draft` is a proposed contract only: `services/api` has no Comms endpoint yet (issue
  #65 unbuilt), so this UI has nothing live to call against. Drafts-only messaging and no
  send/publish action, per `docs/modules/comms-assistant.md`.
- Drafted public-page content in `apps/site/content/` (home, about, events, members, connect) from
  page-specs, executive tone, placeholders for INZBC facts. Ready to drop into Wix.

## SHARED-OK — work taken in this lane by Bhanu

Recorded here, not only in the PR descriptions, per the lane rule in
[docs/workstreams/README.md](README.md). Raised at the next stand-up; object if any of it should
come back.

- **Frontend workspace** (PR #86, 26 Jul 2026). pnpm workspace, Vite + React 19 + TypeScript at
  `apps/fta/ui`, ESLint, Vitest + RTL, generated API client, and the `frontend` CI job with a
  type-drift check. Built to unblock the critical path and to set the pattern you inherit.
- **FTA query component + Storybook** (PR #87). `FtaQuery`, `Answer`, `ActionRequired`, stories and
  the a11y addon. `Answer` and `ActionRequired` are deliberately separate components, not variants.
- **UI correctness fixes** (PR #91). `useId` for ARIA ids, `answer.id` for React keys,
  `box-sizing` reset for 320px reflow, stale-request identity check, deeper response validation.
- **Two member-facing strings still need a named reviewer**: the `<h1>` and intro paragraph in
  `apps/fta/ui/src/App.tsx`. Everything else on screen comes from the API.
- **Still yours:** the design system and brand tokens, the SIP review/approval UI (REQ-U-01/U-02),
  the Comms review UI, the Wix site build, and the accessibility audit.

## Blocked / decisions needed
- Wix MCP connection, for programmatic build (account access is already granted at team level —
  manual build in the Wix editor can start now; see `docs/discovery.md` OI-1).
- Brand kit from Sunil (logo, colours, fonts, photos).
- Membership platform decision (retain/integrate/replace Member Jungle) — build the portal against the choice.
- ~~SIP UI can start once there is a running API.~~ Resolved 26 Jul 2026: `GET /api/fta/query`
  is live (#85) and the frontend workspace with a generated client is in place (#86). The SIP
  endpoints themselves still need the database, scheduled in Phase 2.

## Definition of done
Public site matches the specs and is WCAG 2.2 AA; forms deliver to the right owner; SIP UI lets a
brief be QA'd, approved and packaged for manual send; dashboards read the DB. No pipeline writes.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
