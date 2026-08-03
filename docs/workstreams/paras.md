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
- [ ] Forms UI: confirmation email + owner notification. SHARED-OK: the webhook-to-internal
      delivery (contract + receiver service) moved to Bhanu's worklog.
- [ ] Executive dashboard UI (control state, open actions, QA/distribution status) — reads
      Bhanu's dashboards data-layer endpoints.
- [ ] Final WCAG 2.2 AA audit across every public page (components already carry the behaviour;
      this is the end-to-end verification pass).

## Done
- Member portal link-out shell (`apps/member/ui`, `feat/paras/member-portal-ui`, 9 commits).
  Was asked for as a 16-commit build (branded shell, login, dashboard, profile, a searchable
  member directory, events, resources, Member Jungle link-out, notifications, responsive,
  a11y, loading skeletons). Read against `docs/modules/member-portal-spec.md`'s own "Build
  gate" first: login forms, a dashboard/profile carrying real membership status, and a
  member directory are all explicitly named there as "not buildable until the
  retain/integrate/replace assessment is approved" — the same rule `CLAUDE.md` and
  `docs/modules/membership-crm.md` state (do not rebuild membership on Wix, link out, don't
  duplicate the register; that assessment is still `PROPOSED`, not confirmed). Flagged the
  conflict rather than building against it; scoped down to what the spec's own carve-out
  says *is* buildable now — "a gated shell that sends members to Member Jungle for
  membership, billing, directory and registration... navigation and copy," holding no member
  data.
  Built: branded header/footer (real INZBC logo, same asset already committed under
  `apps/sip/ui`/`apps/comms/ui`) with a "Member Login" link-out to Member Jungle rather than
  a login form (the login mechanism itself — SSO vs. a separate Member Jungle login, Wix
  Members Area at all — is `member-portal.md`'s own unresolved open item, not something to
  build against as an assumption); Membership section (Join/Renew, Directory, Billing, all
  link out to `inzbc.memberjungle.club`, sourced from `apps/site/content/members.md` and
  `client-answers.md` C1/C5); Events section (link out per event to Member Jungle or Zoho per
  C6/C7, using the confirmed "INZBC Summit" name only where illustrative, never a fabricated
  date); Resources and Notifications sections (placeholder-labelled rows only — no invented
  report titles or announcements, per `CLAUDE.md`'s "never invent" rule); a mobile pass
  (Header's four nav links didn't fit one row under 375px — restructured into a logo+CTA row
  plus a horizontally-scrollable nav strip, the same pattern `apps/sip/ui`'s `AppShell.tsx`
  already uses for its screen switcher); a WCAG 2.2 AA pass that found and fixed three real
  defects (an unfocusable skip-link target, three tangerine CTA buttons whose focus ring was
  copied from a navy context onto a white one and fell to ~1.6:1 contrast, and a "Placeholder"
  badge at ~4.34:1, just under the 4.5:1 small-text minimum) — everything else audited clean
  (keyboard access, heading hierarchy, landmarks, focus order).
  Deliberately **not** built: the loading-skeleton commit from the original ask — this shell
  fetches no live data (every screen is static copy or an external link), so a skeleton would
  simulate loading that never happens.
  Not visually verified in a real browser (Chrome tools weren't enabled this session) —
  correctness for layout/contrast was reasoned from Tailwind class values and computed
  contrast ratios, not an actual render; worth an eyeball pass before this ships.
- SIP review/approval UI (`apps/sip/ui`), built against contract fixtures — no live backend
  exists yet (`services/api` has no `/api/reports/*` routes, blocked on migrations, issue #44).
  Four screens per `docs/sip-ui-spec.md`: brief builder (run header, coverage window, candidate
  selection, SIP-186 §12 source-coverage table, required-field validation, submit-for-QA); QA
  review (inline section editing, approve/flag with colour coding, a SIP-188 tri-state checklist,
  send-back-for-correction); CEO decision (digest preview, the four report-decision types with
  required reason/conditions/owner/evidence/next-review-date fields, and — kept genuinely
  separate per the spec's explicit rule — a second, independent distribution-authorisation action
  behind its own confirmation modal); distribution status (read-only QA/decision/distribution
  summary, plus a fixture-backed run archive table). Client-side state-machine enforcement
  throughout (`schemas/state-machine.md`) — the server remains the authority, this is a usability
  layer.

  **Code review on PR #166 found three real bugs in the first pass, all confirmed by running the
  code, since fixed:** (1) QA failed open — N/A on a Critical item didn't count as a fail, an
  empty checklist satisfied "every item answered," and a blank reviewer skipped the
  analyst-conflict check, all three reaching Awaiting CEO Decision with a recorded Pass; (2) the
  mandatory-source gate checked 8 invented codes that matched nothing in the real 112-row SIP-185
  register, so 104 real mandatory sources could never be reported missing; (3) selected candidates
  never reached the generated digest — `submitReportForQa` took a bare count, and selection lived
  in component state that navigating between screens silently wiped. Also fixed: a Critical fail
  now visibly blocks the primary action before submission, not only after; resubmitting after a
  correction starts the checklist fresh and bumps a real `reportVersion` instead of carrying the
  previous round's answers and Fail record forward; `recordCeoDecision` now rejects blank
  reason/owner/evidence/next-review/version server-side, not just via the UI's disabled button;
  the distribution-authorisation modal names the recipient and confirms automated channels are
  off; `GOVERNANCE_LINE` now renders on every screen, not just the CEO decision one; the three
  primary buttons' white-on-tangerine text failed WCAG AA contrast (3.37:1), now navy-on-tangerine
  (5.56:1, verified by the review); CI's frontend test step only ran `@inzbc/fta-ui`, so none of
  this app's tests were ever gating anything — now `pnpm -r --if-present coverage`.

  Fixed a real bug in `reportsStore.ts` along the way: an earlier draft of `recordCeoDecision`
  accepted distribution authorisation in the same call as the report decision, which the spec
  explicitly forbids ("never presented as one combined control") — split into `recordCeoDecision`
  and a separate `authoriseDistribution`.
  **Reconciled against the actual spec, not just the task description that kicked this off**:
  the task's shorthand ("approve/flag buttons," "quality score," "approve and reject buttons")
  doesn't fully match `docs/sip-ui-spec.md`'s real design (a formal SIP-188 checklist, four
  distinct decision types, two sequential CEO decisions) — built the real mechanism and layered
  the requested UI on top rather than one or the other.

  **Still open, not mine to fix:** the CEO decision screen has no role gate at all (documented in
  `CeoDecisionScreen.tsx` rather than faked — needs issue #42's real auth/role model, not a
  stand-in with nothing behind it); the confirmation modal has no focus trap, initial focus,
  Escape handling or focus restoration; the report-decision `role="radio"` buttons have no
  arrow-key/roving-tabindex behaviour. All accessibility gaps, not data-integrity ones.
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
- **Still yours:** the design system and brand tokens, the Comms review UI, the Wix site build,
  and the accessibility audit. (The SIP review/approval UI itself is now Done, above — against
  contract fixtures; still needs the live `/api/reports/*` endpoints and REQ-U-01/U-02 sign-off
  once real data is behind it.)

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
