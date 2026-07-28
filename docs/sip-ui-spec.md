# SIP review and approval UI — spec

Owner: Paras. Covers the three screens in the worklog's "SIP review/approval UI" item: brief
builder, QA checklist, CEO decision — plus a read-only distribution status view. This is a UI
spec against the existing SIP workstream documentation; it does not change any SIP process,
scoring or approval rule. Where this doc and the source documents disagree, the source documents
win, per the same rule `docs/sip/operator-guide.md` sets for itself.

## Sources
- `docs/sip/operator-guide.md` — the full daily-run walkthrough (steps 1–14), roles, stop
  conditions.
- `docs/sip/launch/SIP-186_daily_brief_template_v0.9.md` — the brief's field structure.
- `docs/sip/launch/SIP-188_qa_checklist_v0.9.md` — the QA checklist items, verbatim.
- `schemas/state-machine.md` — the run state machine (states, allowed/illegal transitions).
- `schemas/api-contract.md` — the endpoint shapes these screens call.
- `docs/requirements.md` §3.4 — `REQ-U-01` (QA screen), `REQ-U-02` (CEO decision screen),
  `REQ-U-03` (WCAG 2.2 AA, applies to every screen here).
- `docs/modules/dashboards.md` — the executive dashboard the distribution-status view draws on.

**Not in scope here:** the pipeline/collection UI (candidate capture, source-check recording,
scoring) — that's Roshan's side of `schemas/api-contract.md`. This spec covers Paras's side only:
report review, QA, CEO decision, and status display.

## Roles and separation of duties

| Role | Person (controlled launch) | Screen(s) |
|---|---|---|
| Analyst | Sunil (Bhanu backup) | Brief builder |
| Quality Reviewer | Paras (Roshan backup) | QA screen |
| CEO / SIP Owner | Sunil | CEO decision screen |

The reviewer must not be the run's analyst. This isn't just a UI convention — the platform schema
carries a matching `analyst_id <> reviewer_id` constraint (`operator-guide.md`), and the API layer
enforces it server-side (`api-contract.md`: "a run's analyst cannot be its reviewer; nobody
approves their own output"). **The UI's job is to make the illegal path impossible to reach, not
to be the only thing preventing it.**

## State machine this UI drives

From `schemas/state-machine.md` (states relevant to these three screens, abbreviated):

```
... Report Drafted -> QA In Progress -> Awaiting CEO Decision -> Approved for Manual Distribution -> Distributed -> Closed
                       QA In Progress -> QA Failed -> Report Drafted   (correction + re-review only)
                       Awaiting CEO Decision -> Continue / Continue with Correction / Paused / Stopped
```

Per `REQ-U-01`'s acceptance criteria: **illegal transitions are disabled in the interface,
mirroring this state machine — the server remains the authority.** Every screen below disables
(not just hides) controls that would attempt an illegal transition, and every write still goes
through server-side validation regardless of what the UI allowed the user to click.

---

## Screen 1 — Brief builder (Analyst)

Not formally one of `REQ-U-01`/`REQ-U-02`'s acceptance criteria, but explicitly listed as in-scope
for this UI in the worklog's Next Up item ("brief builder (SIP-186)"). Treat it as part of this
spec; flag to Bhanu whether it needs its own requirement before build (see Open items).

**Entry condition:** run is in `Candidate Review` or later; candidates have been captured and
scored via the pipeline (Roshan's side). The builder assembles the SIP-186 brief from that data —
it is not a blank free-text form.

**API:** `POST /api/reports/daily` (build from selected candidates) · `GET /api/candidates?run=:id`
(pull scored candidates for selection) · `PATCH` on the resulting report for edits before QA
submission.

**Fields — mirror the SIP-186 template exactly, section by section:**

| Section | Content |
|---|---|
| Run header | Run ID, report/brief date, coverage window (start/end, Pacific/Auckland), generated-at, analyst, reviewer, approved version set, source confidence summary, source mix |
| 1. Executive judgement | One paragraph — free text |
| 2. Executive summary | 3–5 bullets |
| 3. Critical and High signals | Per item: headline, what happened, why it matters (NZ / member), signal strength, source confidence, verification status, recommended CEO/member action, primary source URL, register routing, next trigger/review date |
| 4–6. Bilateral developments / Opportunities / Threats | Free text per section |
| 7. CEO action list | Action, owner, priority, due/review date, evidence requirement — repeatable rows |
| 8. Member actions | Free text |
| 9. Watch-list updates | ACT-009, WL-006 — status, verified NZ-specific trigger if any |
| 10. Active carry-forward | Original event, trigger, what changed, what's open, next review date |
| 11. No Material New Signal | Explicit statement, only when applicable — the builder must make this a real, selectable state, not something achieved by leaving everything blank |
| 12. Source coverage and exceptions | Mandatory sources + outcome each (pulled from `GET /api/runs/:id/source-checks`, not re-typed); inaccessible sources + fallback attempts |
| 13. QA and distribution | Read-only in this screen — populated later by Screens 2 and 3 |

**Behaviour:**
- Version label is always `v0.9 Review Draft` (or whatever the current approved-version-set
  convention is) until QA + CEO approval — the builder does not let the analyst mark a report
  "final."
- The governance line ("Human-reviewed. Not authorised for member, external, website or social
  publication.") is rendered on every view of the brief, always, not togglable.
- Section 12 cannot be submitted with a blank outcome against an applicable mandatory source — the
  UI blocks submission and points at the missing source, mirroring the "blank is a Critical stop"
  rule in `operator-guide.md` Step 4. The server still re-checks this; the UI block is a courtesy,
  not the enforcement point.
- "Submit for QA" transitions `Report Drafted -> QA In Progress`. Disabled while section 12 has any
  blank applicable-mandatory-source row.

---

## Screen 2 — QA screen (Quality Reviewer) — `REQ-U-01`

**Entry condition:** run is in `QA In Progress`. Reviewer identity comes from the authenticated
session, not a free field — and if the session's user matches the run's `analyst_id`, the screen
refuses to load and shows why, rather than letting the reviewer start and fail server-side later.

**API:** `GET /api/reports/:id` (load the brief) · `POST /api/reports/:id/qa` (record result).

**Checklist — SIP-188 items, presented one at a time or grouped by the same four sections as the
source document (do not renumber or reword them):**

1. **Authority and versions** — run authority active + date in window + operator authorised;
   approved version set present, no uncontrolled change (**Critical**)
2. **Coverage and sources** — window exactly 24h with timestamps; every applicable mandatory
   source has an outcome (**Critical** if any blank); inaccessible sources show fallback attempts
3. **Content quality** — freshness checked; relevance tests passed; every High/Critical claim has
   official/high-confidence evidence (**Critical**); no High/Critical claim on a snippet/
   inaccessible article/single weak source; duplicates merged; carry-forward correctly labelled;
   No Material New Signal used honestly; facts separated from analysis
4. **Records and routing** — follows SIP-186 structure; every action has an owner + date; register
   routing correct; DB/tracker reconciled (**Critical** if contradictory); evidence retained
5. **Approval and distribution** — human approval recorded before distribution (**Critical** if
   missing); distribution authority/recipient correct; no automated/member/external/website/social
   distribution

**Behaviour:**
- Each item is a tri-state control (Pass / Fail / N/A), not a plain checkbox — SIP-188's own items
  are binary checks, but a Fail on a **Critical**-flagged item must visibly block the "Submit to
  CEO" action; a Fail on a non-Critical item is recorded but does not block.
- **Any Critical failure disables "Submit to CEO" entirely.** The only path forward from a Critical
  fail is "Send back for correction," which transitions `QA In Progress -> QA Failed`. The UI does
  not offer a way to override or bypass a Critical fail — that control does not exist in this
  screen, matching `operator-guide.md`: "A Critical failure is never downgraded to a warning to
  keep the day moving."
- `QA Failed -> Report Drafted` is the only exit from a failed QA — the UI routes back to Screen 1
  with the reviewer's findings attached, not straight back into limbo.
- On a clean pass: `POST /api/reports/:id/qa` records the result, transitions
  `QA In Progress -> Awaiting CEO Decision`, and the CEO decision screen becomes reachable for the
  first time in this run's lifecycle — it is not reachable before this.
- Result fields captured verbatim from SIP-188's own footer: QA result (Pass/Fail), Critical
  failures found, corrections required, reviewer + timestamp.

---

## Screen 3 — CEO decision screen (CEO / SIP Owner) — `REQ-U-02`

**Entry condition:** run is in `Awaiting CEO Decision` (i.e., QA passed). Not reachable from any
earlier state.

**API:** `POST /api/reports/:id/decision`.

**Two separate, sequential decisions — never presented as one combined control:**

1. **Report decision** — exactly one of `Continue` / `Continue with Correction` / `Pause` /
   `Stop`, each requiring reason, conditions (if any), owner, evidence reference, and next review
   date before it can be submitted.
2. **Distribution authorisation** — `Yes` / `No`, a second, independent action. The UI must not
   let the CEO set this in the same submit as decision 1 by default-checking it, pre-filling it
   from decision 1, or otherwise implying approval = permission to send. Per `operator-guide.md`:
   "Approving the report and authorising distribution are two different decisions. Approval alone
   is not permission to send."

**Behaviour:**
- Both decisions are recorded against the **authorised report version** with a **timestamp** —
  the UI reads the version being decided on from the loaded report, not from free text, so a
  decision can never be bound to the wrong version.
- **`Distribution authorised: No` is a valid, complete outcome — not an error or incomplete state.**
  The UI must not show a warning icon, block run close-out, or otherwise treat "No" as something
  to be corrected. The run proceeds straight to close-out with distribution skipped.
- `Pause` and `Stop` are terminal-ish for this run: `Stop` ends the run under this Run ID entirely
  (per the state machine's "illegal transitions" list: `Stopped -> *` is rejected); `Pause` can
  only resume via a recorded resumption approval, which is a separate action outside this screen,
  not a "try again" button here.
- **Nothing in this screen, or anywhere in this UI, offers a "send" action.** Manual send
  (`operator-guide.md` Step 13) happens outside the application by design — there is no automated
  or in-app distribution during the controlled launch. This screen's only output is the recorded
  authorisation; Screen 4 shows what happened afterward, once someone records it.

---

## Screen 4 — Distribution status display (read-only)

Not a workflow screen — a status surface. Two reasonable places for it, not mutually exclusive:
the report detail view (`GET /api/reports/:id`) once a decision is recorded, and the executive
dashboard (`GET /api/dashboard` — "control state, open actions, QA/distribution status", per
`docs/modules/dashboards.md`).

**Shows, per run:**
- Current state (from the state machine) and current run/launch period.
- QA result + reviewer + timestamp.
- CEO decision + reason + timestamp + the report version it was recorded against.
- Distribution authorised: Yes/No.
- If sent (recorded manually, per Step 13): sender, recipient, send time, channel, delivery
  result.
- Close-out status: exceptions, corrections, final run status, backup recorded (per
  `operator-guide.md` Step 14).

**Behaviour:**
- No write controls of any kind on this screen — it renders what `GET /api/reports/:id` and
  `GET /api/dashboard` return. If a field is empty (e.g. no send recorded yet), it shows as
  pending, not as an error.
- This is the only screen a non-Analyst/Reviewer/CEO staff role plausibly needs — it's the natural
  home for "did today's brief go out" without exposing the QA or decision controls to someone who
  shouldn't be able to use them. Role-gating that (view-only vs. the three action screens) is an
  auth decision, not designed here — flagged in Open items.

---

## Cross-cutting rules (every screen above)

- **Fail-closed everywhere**, per `api-contract.md`: a Critical condition returns an error, never
  a warning, from the server — regardless of what the UI allowed the user to attempt. The UI's
  disabled states are a usability layer, not the control.
- **No secrets, no model calls, from the browser.** Every write goes through the authenticated API;
  nothing here talks to a model provider or the database directly.
- **WCAG 2.2 AA (`REQ-U-03`)** — token-driven components (brand tokens now documented in
  `docs/design-decisions.md`), focus order/contrast/keyboard paths built into each component, not
  audited in afterward. These four screens are internal staff tooling, not public pages, so they
  sit outside the public-page audit scope in `docs/accessibility-audit.md`, but the same standard
  applies per `REQ-U-03`'s "As a member or staff user" framing.
- **Everything here reads from and writes to the single Action Register** — the Intelligence
  Database via the API. No screen creates a second, competing register.

## Open items
1. **Brief builder isn't in `REQ-U-01`/`REQ-U-02`'s formal acceptance criteria.** It's in the
   worklog's Next Up item and implied by the workflow, but has no `REQ-U-0x` number of its own.
   Confirm with Bhanu whether it needs one before build, or folds under `REQ-U-01`.
   `[[decision needed]]`
2. These screens are specced against `schemas/api-contract.md`, itself marked "v0.1 draft" — full
   OpenAPI lands as the app is built. Build against contract fixtures now (per the worklog: "no
   live backend" needed to start), but expect the shapes above to move.
3. Role-gating for Screen 4 (who besides Analyst/Reviewer/CEO can view it) is not decided here.
4. Whether the executive dashboard (`docs/modules/dashboards.md`) hosts Screen 4 directly or links
   to a per-run detail view is an open UX call — that module's own "reporting tool: in-app views vs
   Power BI" decision affects it.
5. QA screen's tri-state (Pass/Fail/N/A) per item is a UI design choice, not specified by SIP-188
   itself (which is a plain checklist). Confirm this doesn't conflict with how QA results get
   stored/reconciled against the tracker.
