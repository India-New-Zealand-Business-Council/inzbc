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
- [ ] Design system from `DESIGN.local.md` (not yet created): token-driven component library on
      the real brand tokens documented in `docs/design-decisions.md` (#155) (colours, typography,
      logo rules from the INZBC Brand Guidelines 2026 — no placeholder swap needed, kit already
      arrived), WCAG 2.2 AA behaviour — focus order, contrast, keyboard paths — built into each
      component rather than audited at the end. Two gaps before the library is buildable:
      no font files for Big Shoulders or Merriweather are sourced in the repo, so the typography
      half of the tokens cannot be applied; and the palette's contrast rule has to be enforced in
      the components, not just recorded. `docs/design-decisions.md` now states it: tangerine
      `#f05b29` behind white body-size text is 3.37:1 against the 4.5:1 AA minimum. PR #162's
      primary button had that exact failure, which is what the rule exists to prevent — fixed
      there (navy-on-tangerine, 5.56:1) during review, but the library still needs the rule
      enforced in the components generally, not fixed one button at a time. Two figures in that doc
      still need Sunil's confirmation before they're load-bearing (two-way trade $3.68b vs $3.95bn;
      member count 160+ vs 200+) — don't bake either into a token or copy without it.
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
- [ ] Build the public site in Wix from `apps/site/content/` — content for all seven pages
      (home, about, events, members, trade, partners, connect) is drafted and merged; homepage
      changes are additionally already made in the Wix editor (see `docs/wix-changes-log.md`).
      **Unblocked as of 31 Jul 2026:** OI-9 is closed, the duplicate `INZBC Staging` exists and the
      team have access, so the build can start there. Still do not edit `inzbc.org` directly; the
      duplicate is the only build target until the OI-8 cutover. Programmatic build additionally
      needs the Wix MCP connected (OI-1).
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
- Drafted and rewrote all seven public-page content specs in `apps/site/content/` (home, about,
  events, members, trade, partners, connect) against `INZBC_Website_Migration_Checklist.xlsx` and
  `INZBC_Website_Stocktake_Migration_and_Wix_Guide.docx`, executive tone, `[[placeholders]]` for
  anything not yet confirmed by INZBC. Trade/FTA figures verified against `apps/fta/corpus.py`
  (MFAT Tier 1 sources, 28 Jul 2026). Partners split out of Connect into its own page per the
  migration guide's architecture. All merged to `main`.
- Homepage rebuilt in Wix editor (28 Jul 2026): hero text updated, new FTA Feature Band section
  added after the hero (NZ India FTA Hub heading, Understand the FTA button), HOME 8 reframed as
  "Latest Insights" with FTA/trade-focused copy, HOME 4 "Why choose us?" updated with FTA-focused
  content, HOME 5 "TRADE BAZAAR" renamed to "TRADE WITH INDIA". Saved in the editor, not
  published — pending Sunil's review. Full detail in `docs/wix-changes-log.md` (PR #143). **Note:**
  per `docs/discovery.md` OI-9, this work is sitting unpublished in the live site's editor. The
  duplicate now exists, so it needs redoing there from the log above, and the live editor rolled
  back via Site History.
- Documented homepage/About design decisions in `docs/design-decisions.md`, sourced
  from the full INZBC Brand Guidelines 2026 (colours, typography, logo rules), the migration
  checklist and the Wix guide — including two unresolved figure conflicts flagged for Sunil, not
  silently picked.

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
- Wix MCP connection, for programmatic build (`docs/discovery.md` OI-1) — **and** manual editor
  work is now also blocked: per OI-9, live-site editing has stopped pending Sunil duplicating the
  site and adding the team as collaborators there. Do not edit `inzbc.org` in the meantime.
- ~~Brand kit from Sunil~~ Resolved 29 Jul 2026: INZBC Brand Guidelines 2026 (colours, typography,
  logo rules) found in Drive and documented in `docs/design-decisions.md`. Logo asset files
  (svg/png/jpg) and approved photography still not supplied — see that doc's Open items.
- Membership platform decision (retain/integrate/replace Member Jungle) — `docs/client-answers.md`
  C1 proposes retain-and-integrate, but it's `PROPOSED`, not Sunil-confirmed. Build the portal
  against the confirmed choice, not the proposal.
- ~~SIP UI can start once there is a running API.~~ Resolved 26 Jul 2026: `GET /api/fta/query`
  is live (#85) and the frontend workspace with a generated client is in place (#86). The SIP
  endpoints themselves still need the database, scheduled in Phase 2.

## Definition of done
Public site matches the specs and is WCAG 2.2 AA; forms deliver to the right owner; SIP UI lets a
brief be QA'd, approved and packaged for manual send; dashboards read the DB. No pipeline writes.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
