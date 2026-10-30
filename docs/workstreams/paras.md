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
Design: follow `docs/design-direction.md`. Do not invent a look; brand tokens come from INZBC's kit.

## Modules I own (see [docs/modules](../modules/README.md))
[Public website](../modules/website.md) + [Member portal](../modules/member-portal.md) +
[Events & delegations](../modules/events-delegations.md) + [Dashboards](../modules/dashboards.md) +
SIP review/approval UI + Comms Assistant UI + FTA Explainer embed.

## Depends on
The shared API + auth for anything that reads/writes data. Roshan's FTA service for the Explainer UI.

## Next up — 8-week plan, Studio 6 (from 10 Oct 2026)

Rewritten from scratch against the real repo state, not the previous draft of this file: v1.0.0
shipped 10 Sep 2026 (`CHANGELOG.md` — v0.1.0 landed 9 Sep, v1.0.0 and the same-day v1.1.0 fixes on
10 Sep) with a real Postgres database, a real API, and the SIP UI reading real runs and candidates
instead of fixtures. Several items below that used to be blocked are now unblocked, and one whole
item (the Wix site build) is **obsolete** — the public site moved to a different stack entirely
while this file was last updated. Read `## Stale items to retire` before trusting anything that
still sounds like late July.

Ordered by what actually blocks the next thing, not by week number — but a rough shape for an
8-week block. **Correction from the part-time reality, not full-time** — ADR-0008 (#382) is built
on three part-time engineers sharing one client, and this list is bigger than that budget. A
must-do line, so it's clear what drops first if the block runs short rather than discovering that
in week 7:

**Must-do (as of 26 Oct, see the lane-pivot Done entry below):** small, real, daily-commit-sized
fixes/polish on `apps/sip/ui`'s two agent surfaces (the coordinator-agent rehearsal panel, the
platform assistant), plus one research thread a week for the course's own requirement — not the
items below, which are paused, not abandoned.

**Paused, not abandoned — client asked not to touch the live public site further (26 Oct 2026):**
- `inzview` work of any kind, including the two items below.
- The 320px reflow Playwright case and the `inzview` gap list are both done (see Done); nothing
  further needed there regardless.
- The manual half of the final WCAG 2.2 AA audit (REQ-U-03) — automated sweep is done (see
  Done), but the remaining keyboard-only pass, NVDA/VoiceOver pass and post-publish re-scan all
  depend on `inzview` being touched/published again. Pick back up if that changes.
- **Forms UI: confirmation + owner notification** — built (`inzview` `8a260cc`, 25 Oct 2026),
  see Done below. Delivers nowhere until the platform API and its database are hosted (decision
  3 in `decisions-needed.md`) and nothing can be re-verified live while `inzview` is paused.
- **FTA Explorer embed, deployed** — blocked on embedding into `inzview`, which is paused.

**Still active, not `inzview`-dependent:**
- [ ] **Comms Assistant review UI.** #60 is closed in GitHub, but check what it actually shipped
      against before assuming the reviewer-approval screen exists — the service side
      (`services/api/comms.py`, draft + approve + delete endpoints) is real and live; confirm
      whether a UI was ever built against it or whether #60 was closed for a narrower reason.
      Drafting UI (`apps/comms/ui`) and the delete-draft flow are both Done, below.
- [ ] **#129/#127/#128 — the rest of the Playwright E2E suite,** once #100's 320px case (above)
      has landed and set the pattern. Client-side state-survives-a-refresh and
      illegal-action-rejected cases matter more now there's a real backend to test against, not
      fixtures.

**Weeks 6–8 — design system, member portal depth, and whatever the gap list surfaced**
- [ ] **#58 Design system from `docs/design-direction.md`.** Token-driven component library on the
      real brand tokens (`docs/design-decisions.md`), WCAG behaviour built into each component
      rather than audited after. Two blockers to check first, not assume still true: are Big
      Shoulders/Merriweather font files sourced yet, and is the tangerine-contrast rule (3.37:1,
      below the 4.5:1 minimum — the exact bug PR #162 shipped and review caught) enforced in
      components generally, or still only fixed where someone happened to notice.
- [ ] **#198 Member portal: gated resources, renewals, briefings, request forms** — real depth
      beyond the current link-out shell. **Hard gate, check before starting:** the
      retain/integrate/replace decision for Member Jungle is still open (see Blocked, below). Login
      forms, a real dashboard/profile and a member directory are explicitly out of scope until
      that's resolved — confirm it's resolved before touching any of those three.
- [ ] **#199/#200 Events/delegations and Sponsors/trade services** — scope these properly rather
      than starting blind; both are large, multi-actor modules (`docs/modules/events-delegations.md`,
      `docs/modules/sponsors-trade-services.md`) that likely split the way SIP's UI did.
- [ ] **#69 Frontend testing & tooling stack** (Storybook, Chromatic) if time remains — lower
      priority than the above since Vitest/RTL/Playwright already cover correctness; this is
      visual-regression tooling, a nice-to-have against an 8-week budget, not a blocker for anything
      else on this list.

## Stale items to retire — read before trusting the old plan

- **"Build the public site in Wix from `apps/site/content/`" is gone, not done.** This file
  previously planned a Wix Studio build. That never happened — the whole site moved to **Wix
  Vibe** (Astro/React/Tailwind) in the separate `inzview` repository instead
  (`ADR-0007`), and nearly all 209 commits there are already yours. If anyone — including a future
  read of this file — cites the old Wix-Studio plan, it's wrong; point them at `inzview` and
  `ADR-0007`.
- **"CMS collection schemas mapped to page-specs... ready to create as dynamic pages"** was written
  against the Wix-native CMS plan above. `inzview` is a plain Astro/React site with content in
  `src/components/inzbc/content.ts` per `ADR-0007` — there is no Wix CMS to map collections into on
  this stack. Re-scope as "how does dynamic content work on `inzview`" if it's still needed, rather
  than carrying the old Wix-shaped task forward unchanged.
- **#329 (container diagram) and #330 (UI integration patterns + screen flow)** were the prior
  top-priority item here — both shipped (PRs #340, #341) and are recorded in Done, below. Don't
  re-open them.

## Done
- **Friday a11y/keyboard pass on both agent surfaces** (PR #507, 30 Oct 2026, refs #62).
  Reviewed `AgentRehearsalPanel.tsx` and `PlatformAssistant.tsx` against keyboard operability,
  live-region usage and color-only signalling. Real gap found and fixed: the rehearsal list's
  expand/collapse button had `aria-expanded` but no `aria-controls`, so a screen reader
  announced the toggle state with no programmatic link to the region it opens — fixed with a
  stable id per rehearsal's detail region, the standard WAI-ARIA disclosure pattern, one new
  test. Nothing else real found: every interactive control in both files is already a native
  `<button>`, loading/error states already use `role="status"`/`role="alert"`, and every status
  distinction pairs a text label with color. Not claiming a clean bill beyond what this pass
  actually checked (no axe run, no live screen-reader pass — see `docs/accessibility-audit.md`
  for what that would still take).
- **Lane pivot, 26 Oct 2026: off `inzview`, onto polishing the agent-facing UI in this repo.**
  The client doesn't want the live public site touched further right now (risk of breaking a
  production site someone else owns the fallout for). Remaining work shifts to `apps/sip/ui`'s
  two agent surfaces — the coordinator-agent rehearsal panel and the platform assistant — small,
  real, daily-commit-sized fixes and polish, plus one research thread per week for the course's
  own requirement to show work beyond frontend/backend. Week plan: Mon fix, Tue polish, Wed
  research, Thu apply a finding, Fri test/a11y pass, Sat buffer, Sun sync + report.
- **Research: surfacing agent trust and reasoning in the UI** (PR #484, 28 Oct 2026, refs #62).
  Six sources, each checked against its real record (DOI/ACL Anthology/Zenodo) on 28 Oct 2026 —
  see `docs/research/agent-transparency-ui-literature-review.md`. Complementary to Bhanu's
  `agent-safety-literature-review.md`: his asks how the agent is constrained, this asks how the
  interface should represent what it did. One concrete finding to act on Thursday: a rehearsal's
  refused step has no more visual weight than the accepted steps around it.
- **Fix: platform assistant's disclaimer cleared on New conversation** (PR #467, 26 Oct 2026,
  refs #62). "New conversation" cleared `messages`/`error` but left `disclaimer` untouched, so a
  stale disclaimer from the previous conversation could linger under the input after starting a
  fresh one. Found by reading `PlatformAssistant.tsx` end to end before touching it, not guessed
  at. One-line fix, one new test (256/256 passing after).
- **Add a Refresh control to the agent rehearsal panel** (PR #478, 27 Oct 2026, refs #62). The
  rehearsal list only loaded once on mount — no way to see a rehearsal started elsewhere
  (another tab, another reviewer) without reloading the page. Reuses the same abort-in-flight
  pattern as `ExecutiveOverview`'s `fetchDashboard` (#61's own fix, PR #437's follow-up): a
  slower older response can never overwrite a newer one, unmounting aborts whatever is still
  pending. One new test (257/257 passing after).
- **Forms UI: both `inzview` contact forms submit for real** (`inzview` `8a260cc`, 25 Oct 2026,
  refs #45). Connect's `ContactForm` and Home's quick-contact form were mailto-only — honestly
  labelled as such, but nothing reached the Secretariat unless the visitor's own client sent it.
  Both now POST to a new `src/pages/api/site-forms.ts` (Astro SSR route, `inzview`'s stack is
  `output: "server"`): it signs the submission (HMAC-SHA256 over `<timestamp>.<body>`, matching
  `schemas/webhooks.md`'s contract, #45) with `WIX_WEBHOOK_SECRET` and forwards to the platform's
  receiver at `INZBC_API_BASE_URL`. **Neither env var is set yet** — the platform API has no
  public host — so the route returns `not_configured` (503). `src/lib/siteForms.ts`, the shared
  helper, falls back to the previous mailto draft on that or any other non-OK response or
  network failure, so there is never a dead "Send" button. Not run through `astro
  check`/`vitest` — `inzview` can't install dependencies locally (`@wix/locale-dataset-javascript`
  is on Wix's private registry, `inzview/HANDOVER.md` already documents this) — reviewed by eye
  against the webhook contract instead.
  - *Still open (checked by Bhanu Gupta, 25 Oct 2026):*
    - **Hosting dependency.** #99 alone does not unblock delivery. #99's free-tier deploy is
      the FTA slice with no database, and the receiver refuses with 503 until `DATABASE_URL` is
      set. Delivery needs the platform API and Postgres hosted (decision 3, "Platform hosting",
      in `decisions-needed.md`), the same `WIX_WEBHOOK_SECRET` set on both that deployment and
      `inzview`'s Vibe deployment, and `INZBC_API_BASE_URL` on `inzview`.
    - ~~**Copy.**~~ Fixed (`inzview` `b9052d5`, 25 Oct 2026). Both forms' idle-state text and
      Home's button label reverted to the honest mailto-opening wording they had before this
      week's change — no longer promises direct delivery ahead of a visitor actually hitting
      the fallback.
    - **Browser pass.** Still needs the real browser/editor pass `inzview/HANDOVER.md` calls
      for, then re-verification against the live receiver, once published.
- **Verified the 23–24 Oct merge wave against this repo** (24 Oct 2026). A large batch of Bhanu's
  work landed overnight (sealed agent audit, agent-rehearsal panel, platform assistant, module
  onboarding across all five UIs, the platform-wide WCAG scan below, replay/adversary eval work).
  Re-ran everything after pulling: full Python suite (1,526 passed, 3 skipped, 0 failed),
  frontend lint and the full frontend test suite, all clean — no regression from the volume of
  change. Local dev Postgres (`inzbc-dev-pg`) was missing migrations 0005–0007 (site forms,
  decision signatures, agent rehearsals); applied before re-running so the Python suite wasn't
  failing against stale schema rather than real code.
- **Automated WCAG 2.2 AA sweep across every app and the live site — done, SHARED-OK** (24 Oct
  2026). Bhanu did the actual sweep: an axe scan of all ten platform screens plus the FTA
  Explainer (`e2e/platform.spec.ts`, `e2e/fta-a11y.spec.ts`, `docs/accessibility-audit.md`), one
  real fix in `apps/sip/ui` (the overview's control-card code references under 4.5:1 contrast),
  and separately an axe scan of the live `inzview` site itself fixing five real failures: the
  home gallery counter at 4.11:1 and a non-focusable photo strip, a `dl` with two wrapper `div`s
  around each `dt`/`dd` pair on the India Market Opportunities page, 60%-opacity body text at
  3.54:1 on Sponsors/Membership/contact-form/social-feed pages, and an FTA review note at 4.43:1.
  Not something I need to redo — recorded here since it is the automated half of this list's
  WCAG Must-do item, and because it reached deep into my lane (see SHARED-OK, below). The manual
  half (keyboard, screen reader, post-publish re-scan) stays open under Weeks 1–2.
- **#61 Executive dashboard, first real slice** (PR #437, 23 Oct 2026). Replaced the client-side
  composition (`listRuns()[0]` + `listCandidates(run.id)`, tallying verification states in
  TypeScript) with `ExecutiveOverview`, reading Bhanu's real `GET /api/dashboard` endpoint (#47,
  closed): current run, candidate coverage, QA/distribution gates, and the open-actions panel —
  previously unreachable since `action_register` had no endpoint at all. Deleted the now-dead
  `candidatesClient`/`runsClient`/`candidateSummary` modules and their tests. Also fixed a
  cross-app break the first pass missed: `apps/sip/ui`'s `PlatformOverviewScreen` imported the
  deleted `SipOverview` via the `@dashboard` Vite alias — repointed at `ExecutiveOverview`.
  Board/measures scorecards (membership, trade/FTA, sponsors) still not built — `ComingSoon`'s
  copy corrected to say so, since #47 closing unblocked the executive view, not those.
- **#292 QA review interface — self-verification exception UI** (PR #435, 23 Oct 2026). The
  checklist half (item-by-item SIP-188, Critical blocks CEO decision, reviewer-cannot-be-analyst)
  was already confirmed end-to-end back in August (see the issue's own comment thread) — this
  closed the remaining gap: a real UI state for the `/api/candidates/{id}/verify` 403 a
  self-verifying reviewer hits, distinguishable from the generic error toast the issue explicitly
  asked not to ship. Both 403s on that endpoint carry the same `code: "http_error"`
  (`services/api/hardening.py` gives every `HTTPException` the same code), so
  `isSelfVerificationError` discriminates on message text instead. Adds an exception-id field and
  a distinct alert; exception-row creation itself stays out of scope, tracked by #348's own
  explicit two-track split.
- **#100 Playwright E2E suite for the FTA query flow, including the 320px reflow case** (21 Oct
  2026). Runs against the real running service (no mock) — the same two queries the `docker` CI
  job already curls at the HTTP level (`q=wool` matches, `q=zzzznotathing` doesn't), now asserted
  through the actual rendered UI. Wired into the `docker` CI job (reuses its already-built,
  already-healthy container rather than standing up a second server — the FTA path needs no
  database, so there's nothing cheaper to start).

  **Found a real bug the manual "one-off Chromium measurement" (this issue's own description of
  the prior state) had missed:** `index.css` sets the root font-size to 112.5% (18px, not the
  browser default 16px) — sitewide, intentional, present in all five apps. `FtaQuery.tsx`'s input
  wrapper used Tailwind's `min-w-72` (`18rem`), which at this site's actual rem size computes to
  324px — wider than a 320px viewport outright, before the Search button even got a chance to
  wrap below it. The reflow test failed against the unmodified component (324px measured, by
  instrumenting every element's bounding box rather than guessing which one), confirming this
  was a real, previously unguarded regression, not a hypothetical one. Fixed with a pixel
  min-width (`min-w-[220px]`), immune to the rem-scale surprise; typecheck, lint and all 38
  existing unit tests still pass. Re-ran the reflow test against the fix: passes.
- **#196/#197 site-rebuild issues closed as superseded** (21 Oct 2026). Both predated the Wix
  Studio→Vibe move; `inzview` is the real, live, client-reviewed rebuild (hosted on `inzbc.org`
  as of 20 Oct 2026), so "rebuild on the Wix duplicate" and "map content for that rebuild" no
  longer describe live work. Closed with a comment explaining why rather than silently dropped.
- **`inzview` gap list written down** (`HANDOVER.md`, 20–21 Oct 2026) — the actual Week 2
  deliverable this file's own plan called for. Real findings, not a restatement of the old list:
  `SITE_ORIGIN` in `seo.ts` was still pointing canonical/sitemap/og:image URLs at the Wix Vibe
  preview host after the domain cutover had already happened (found and fixed same day, commit
  `b5be70e`); both contact forms are mailto-only, honestly labelled as such but not a real
  submission; news/events/sector content has no CMS, just hardcoded TypeScript per ADR-0007 — a
  new-build decision for INZBC, not something this repo can close by itself. Also dropped three
  stale items the list had been carrying since August (individual partner logos, a since-passed
  date-correction note) now that the real state has moved past them.

- **CEO Decision screen wired to the real decision endpoints** (PR #361, closes #293). Rescued
  from a stranded branch (#352/#353 were abandoned when Bhanu's reconciliation in #357 landed the
  real `/ruling`/`/approval`/`/distribution` endpoints instead) — rebased the one real UI commit
  onto `main`, then found and fixed a genuine contract drift: `idempotency_key` had become
  caller-supplied during #357's reconciliation and the stranded commit predated that, so every
  decision POST would have 422'd. Bhanu's review then found four real data-integrity blockers, all
  fixed and re-reviewed before merge (9 Sep 2026): `Authorised` was offered from `Continue With
  Correction`, a state ADR-0005/REQ-G-04 can never accept it from; the free-text Owner field
  displayed as if it were the authoritative record when the real audit record is the signed-in
  account; `idempotency_key` was regenerated per call instead of once per submission attempt,
  defeating its own purpose on a retry; and the distribution control offered itself with no check
  that Report Approval was ever recorded, which in the live flow it never can be since no screen
  writes it. Fixed with a client-side readiness check (`fetchDistributionReadiness`) rather than
  building the missing approval screen, which stayed a separate scope question.
- **Dashboard rebranded to match the live inzview build** (PR #362, refs #58/#61). Found by
  comparing it side-by-side against SIP/Comms/FTA/Member: Dashboard was the one app the original
  branding pass (#333) never touched — still Big Shoulders/Merriweather, lavender accent, a local
  logo SVG, a docked navy header, `max-w-4xl`. Brought in line: Poppins, the ink/deep/mist tokens,
  the floating glass-pill header (no CTA in its third slot — no membership action fits an
  internal-only tool), the real logo, lime accent, `max-w-7xl`.
- **Comms draft delete** (PR #355, closes #343 and #342). `DELETE /api/comms/drafts/{id}` —
  rebuilt after finding the endpoint didn't actually exist despite an earlier issue claiming it
  shipped. Secretariat/SIP Owner roles, a required reason (1–500 chars, in the body not a query
  parameter so it never lands in access logs), any status deletable including Approved, `SELECT
  ... FOR UPDATE` so a concurrent approval can't land mid-delete, and the audit row never carries
  the deleted text — only the status transition, since `audit_log` is append-only and copying the
  text in would make it permanently unremovable. UI: delete is two steps (reason, then confirm),
  never one click, with a stated reason since it feeds a record that can't be edited afterward.
- **C4 container diagram for the whole platform** (#329, PR #340) and **UI-to-API integration
  patterns + SIP screen-flow diagrams** (#330, PR #341). The repo had Level 1 (context) and one
  Level 3 (component) diagram and nothing at Level 2 — all five UIs appeared in no diagram
  anywhere. Drew shells as shells rather than implying more than existed at the time.
- **Runs/Candidates review screen** (#263) — the four candidate commands (verify/score/route/merge)
  against `services/api/candidates.py`, each a plain database write with its own guard (the
  verification gate re-checked at score, route and inclusion; same-person-can't-verify-then-score).
- **Branding matched to the live inzview build** across FTA/Comms/SIP/Member (#333) — Poppins,
  the floating glass-pill header, lime replacing lavender/tangerine, the real Wix Media logo, and
  the `max-w-7xl` width-and-type-scale pass. Dashboard was missed in this round and caught later
  (above).
- **`inzview` — the live public website**, essentially built single-handedly: 209 commits, real
  content fixes found and corrected along the way (a stale "last issue Dec 2023" when the real one
  was June 2024, a tariff figure missing its base percentage, a partner logo rendering at 0×0), and
  one real traced bug — Wix's Embed Code element sandboxes its iframe with no way to grant
  top-navigation access, so plain `<a target="_top">` links were silently swallowed; fixed per
  Wix's own documented `postMessage()`/`onMessage()` pattern, scoped to the real site origin rather
  than a wildcard target (MDN's own warning against `"*"`). This whole line of work is not reflected
  anywhere else in this file before this rewrite — the previous version of this worklog still
  planned the site as a Wix Studio build that never happened. See `## Stale items to retire` below.
- Member portal Dashboard (`apps/member/ui`, `feat/paras/member-dashboard`, 11 commits) — the
  main overview screen on top of the link-out shell (issue #198, PR #217). Not a routed page:
  no router exists anywhere in this codebase and this app has exactly one screen, so `Dashboard`
  is a page-level component `App.tsx` renders above the existing full Notifications/Membership/
  Events/Resources sections, which are unchanged below it. Four summary widgets
  (`src/components/dashboard/`) reuse the full sections' own data — moved each section's
  placeholder constants into `src/lib/*Data.ts` so both the widget and the full section import
  the same array rather than risking two copies drifting apart — and link down to the matching
  full section via the same in-page anchors (`#notifications` etc.) Header's nav already uses.
  Widgets sit in a responsive grid: 1 column mobile, 2 at `sm`, 4 at `lg`.
  Also fixed, as its own early commit since it affects the whole app: the shared layout was
  capped at `max-w-2xl` (672px), leaving large dead margins on desktop/laptop. Widened to
  `max-w-7xl` (1280px) via a new shared `Container` component used by Header, Footer and
  `App.tsx`'s main content, so the width is consistent across the app rather than patched on
  the Dashboard alone.
  Accessibility pass found one real gap beyond the reused-safe colour/focus patterns already
  established: the four cards were bare `<div>`s with no group semantics, so a screen reader
  user tabbing through the grid had no signal of where one card's content ended and the next
  began — added `role="group"` + `aria-labelledby` (via `useId`, same pattern
  `apps/sip/ui`'s `BriefBuilderScreen` uses) to each card. Mobile pass found the widgets' bare
  text links were ~20px tall, under WCAG 2.5.8's 24px tap-target minimum — padded with
  `-mx-1 px-1 py-1` (cancels out visually, pads the hit area) rather than changing the visible
  spacing.
  Not visually verified in a real browser this session (Chrome tools weren't enabled) —
  verified via Testing Library (44 tests) and reasoning about Tailwind class values, not an
  actual render at each breakpoint; worth an eyeball pass at mobile/tablet/desktop widths
  before this ships.
- Member portal link-out shell (`apps/member/ui`, `feat/paras/member-portal-ui`, 9 commits).
  Was asked for as a 16-commit build (branded shell, login, dashboard, profile, a searchable
  member directory, events, resources, Member Jungle link-out, notifications, responsive,
  a11y, loading skeletons). Read against `docs/modules/member-portal-spec.md`'s own "Build
  gate" first: login forms, a dashboard/profile carrying real membership status, and a
  member directory are all explicitly named there as "not buildable until the
  retain/integrate/replace assessment is approved" — the same rule `PROJECT-RULES.md` and
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
  report titles or announcements, per `PROJECT-RULES.md`'s "never invent" rule); a mobile pass
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
- **SIP agent-rehearsal panel** (PR #449, refs the sealed-audit work in #448). A "Coordinator
  agent" panel on the Run Detail screen (`apps/sip/ui`) — staff can run the SIP coordinator agent
  over an in-memory copy of a run (never the persisted one), see its outcome, step trail, and
  whether the hash chain/seal/replay still verify. Server side: `POST /api/runs/:id/agent-rehearsals`
  plus list/get, append-only `agent_rehearsals` storage (migration 0007).
- **SIP role-aware Getting Started walkthrough** (PR #450, refs #62). First visit to `apps/sip/ui`
  opens on a new "Getting started" screen instead of the overview — reads `GET /api/session`,
  shows one card per role (Analyst/SIP Owner/Reviewer/Secretariat), and builds each step's list
  from the real `write_access(...)` roles on that route so it never promises an action that
  answers 403. Stacked on #449 (one Analyst step links to the rehearsal panel).
- **Module onboarding + platform assistant, all five UIs** (commit `203a865`, refs #62, 24 Oct
  2026). `ModuleWelcome`/`Welcome` components added to `apps/comms/ui`, `apps/dashboard/ui`,
  `apps/fta/ui`, `apps/member/ui` and `apps/sip/ui` — a first-visit introduction per module,
  dismissed per module, one click away after. Also a read-only chat assistant on the SIP platform
  home (`PlatformAssistant.tsx`, `POST /api/assistant/chat`): three fixed read-only tools (FTA
  corpus with citations, recent run metadata, a fixed platform guide), no writes, no storage,
  redaction applied like every other model call. Touches `PlatformOverviewScreen.tsx` again (on
  top of the accessibility fix below).
- **Platform-wide WCAG scan + accessibility fixes** (commit `2a4c2ff`, refs #189, 24 Oct 2026).
  Recorded above under Done (the automated half of this list's WCAG Must-do item) — noted here too since it
  edited `apps/sip/ui/src/screens/PlatformOverviewScreen.tsx` directly (a contrast fix on the
  control-card code references).
- **Accessibility fixes on the live `inzview` site itself** (commit `a003d9f` on the `inzview`
  repo, 24 Oct 2026) — also recorded above under Done. Flagging separately because this is a
  different repo than the rest of this section: `inzview` has been built single-handedly by me
  (see Done, below, "`inzview` — the live public website"), and Bhanu has **19 commits on `inzview`'s
  `main` since 21 Oct** (33 in total), 17 pushed directly and 2 through PRs (#11, #12): home
  gallery photos, FTA sector-card corrections, a Partners page, chapter-list updates, social
  links, among others —
  worth raising at stand-up given the scale, not because anything found was wrong.
- **Still yours:** the design system and brand tokens, the Comms review UI (check #60's actual
  scope before assuming it's unbuilt — see Next up), the manual accessibility checks (keyboard
  and screen-reader passes, and the post-publish re-scan of inzbc.org; see Weeks 1–2), and the public site
  — now `inzview` (Wix Vibe), not the Wix Studio build this line used to name. (The SIP
  review/approval UI is Done, above, and has been reading real data since v1.0.0 shipped 9 Sep
  2026 — the "still needs the live endpoints" caveat that used to be here no longer applies.)

## Blocked / decisions needed
- **Membership platform decision (retain/integrate/replace Member Jungle) — still the real
  blocker, check before starting #198.** `docs/client-answers.md` C1 proposes retain-and-integrate,
  but as of this rewrite it's still `PROPOSED`, not Sunil-confirmed. Build the portal against the
  confirmed choice, not the proposal — login forms, a real dashboard/profile and a member directory
  all stay out of scope until this resolves.
- ~~Brand kit from Sunil~~ Resolved 29 Jul 2026, logo assets since sourced and in use across every
  app (`docs/design-decisions.md`'s Open items from this period are stale — check that doc directly
  rather than trusting this line's age).
- ~~Wix MCP / OI-9 live-editor block~~ **Moot, not resolved** — the site moved to `inzview`
  entirely, so the Wix Studio editor constraints this used to name no longer apply to where the
  real work happens. If Wix Studio editing of `inzbc.org` itself is ever needed again (unlikely
  given the `inzview` move), re-check OI-1/OI-9's live status before assuming either way.
- ~~SIP UI can start once there is a running API.~~ Resolved — long since superseded by v1.0.0
  (9 Sep 2026): real Postgres, real API, SIP UI reads real runs and candidates.

## Definition of done
Public site (`inzview`) matches the gap list from Next up and is WCAG 2.2 AA; forms deliver to the
right owner; SIP UI lets a brief be QA'd, approved and packaged for manual send, against real data
(already true since v1.0.0); dashboards read the DB for real, not just the SIP slice. No pipeline
writes.

Base: main @ 5eee5df (24 Oct 2026) — record when you start a task; rebase if behind.
