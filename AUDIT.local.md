# INZBC project audit — resumable research state

**Purpose:** drive the project to a standard that (a) satisfies Sunil as client, (b) clears every
Studio 5 objective with evidence, (c) gives Bhanu depth in platform / AI / security engineering and
Roshan + Paras enough evidenced workload to pass. Private working file, gitignored.

**How to resume:** read "Status board" then continue at the first `TODO` phase. Each phase ends with
a Codex adversarial review, then fixes, then the next phase.

---

## Status board

| Phase | What | State |
|---|---|---|
| 0 | Inventory repos + all project documentation | DONE |
| 1 | Gap analysis vs Studio 5 objectives + SCRUM contract promises | DONE (findings below) |
| 2 | Fix P0 defects (doc drift, single source of truth) | DONE — PR #72 + agent #12 merged |
| 3 | Diagrams (ERD, architecture, run-flow, sequence) | DONE — PR #71 merged, corrected after audit |
| 4 | User documentation (operator guide) | DONE — PR #72 merged, corrected after audit |
| 5 | Requirements formalisation (user stories + acceptance criteria + traceability) | DONE — PR #72 merged |
| 6 | Meeting minutes / ceremony records | DONE — PR #73 merged |
| 7 | Weekly progress report + timesheet system | DONE — `Desktop\Studio5-Submissions\`, week 1 pre-filled |
| 8 | Per-member PDR evidence packs | TODO |
| 9 | ADR-0002 internal platform hosting | DONE — process-not-service, with graduation trigger |
| 10 | Paras's stranded branches into PRs | DONE — PRs #74-79 opened; #79 flagged on figures |
| 11 | Reflective report structure (each learner writes their own prose) | TODO |
| 12 | Client acceptance / handover record | TODO |
| 13 | Ethics, legal and professional considerations consolidated for 2.1 | TODO |
| 14 | Portable evidence snapshot (not dependent on private repo access) | TODO |

Rule: after each phase → Codex adversarial review → fix findings → next phase.

---

## Phase 0 — Inventory (DONE)

### Repos in the org
| Repo | Lang | Role |
|---|---|---|
| `inzbc` | Python | Main monorepo: site content, SIP, FTA, collector, services, schemas, docs |
| `daily-india-nz-news-agent` | Python | SIP collection engine; runs the live daily digest |
| `demo-repository` | HTML | GitHub sample repo. Noise — not part of the project |

### Documentation map

**inzbc (35 markdown docs)**
- Governance//rules: `CLAUDE.md`, `CONTRIBUTING.md`, `.github/pull_request_template.md`
- Strategy/discovery: `docs/discovery.md`, `docs/inzbc-ai-operating-system.md`,
  `docs/ai-service-architecture.md`, `docs/inzbc-talking-points.md`, `docs/page-specs.md`,
  `docs/services-agreement-draft.md`, `docs/client-comms-drafts.md`, `docs/sunil-requests.md`
- Module specs: `docs/modules/` (website, membership-crm, member-portal, comms-assistant,
  fta-centre, dashboards, events-delegations, sponsors-trade-services, README)
- Contracts (system specs): `schemas/api-contract.md`, `schemas/state-machine.md`,
  `database/schema.sql`
- Decisions: `docs/decisions/0001-backend-language.md`, `0003-frontend-tooling.md`
- SIP controlled docs: `docs/sip/README.md`, `build-plan.md`, `SIP_Reference_Config.json`,
  `docs/sip/launch/` (SIP-050 v1.1, SIP-184, SIP-185, SIP-186, SIP-188, launch-config,
  daily-run-record, README)
- Domain: `docs/fta-source-corpus.md`, `docs/information-standard.md`
- Process: `docs/workstreams/` (README, bhanu, roshan, paras)

**daily-india-nz-news-agent (12 markdown docs)**
- `README.md`, `CLAUDE.md`, `CONTRIBUTING.md`, PR template
- `docs/sip-launch/`: SIP-184, SIP-185, SIP-186, SIP-188, launch-config, daily-run-record,
  README, **backup-procedure_v0.9.md** (exists only here)

---

## Phase 1 — Findings

### P0 — controlled documents duplicated across repos, and drifted
The SIP launch SOPs exist in BOTH repos. Verified by diff:

| Document | State |
|---|---|
| SIP-184 daily run SOP | **DRIFTED** (4 lines) |
| SIP-185 source register | **DRIFTED** (20 lines) |
| SIP-186, SIP-188, launch-config, daily-run-record, README | identical |
| SIP-050 master prompt v1.1 | only in `inzbc` |
| backup-procedure v0.9 | only in the agent repo |

`inzbc` holds the **current** copies. The agent repo's SIP-185 is missing the 22 Jul 2026 outcome-code
reconciliation: the canonical six codes, `Excluded` sub-reasons, operational extras, and the explicit
note that **`No Material New Signal` is a day-level conclusion, not a per-source outcome code**.

Why it matters: an operator following the agent repo's copy during the 27–31 Jul launch records
outcome codes that do not match the reconciled list or the DB enum
(`Included, Context, Suppressed, Inaccessible, Excluded, No Qualifying Item`). This is exactly the
error an external assistant made when asked to describe the process. SIP's own control model requires
one controlled version of a controlled document.

**Fix:** one source of truth in `inzbc`; the agent repo links to it rather than holding copies. Move
`backup-procedure_v0.9.md` into `inzbc` alongside the rest.

### P1 — the SCRUM contract promises artifacts that do not exist
The signed contract commits the team to these. Verified absent from the repos:
- **Meeting minutes** ("minutes taken on rotation") — none exist
- **User stories with acceptance criteria** — issues exist, but not in story form with AC
- **Sprint planning / retrospective records** — none exist
- **User documentation** ("user documentation for the review flow and public site") — none exists
- **ADR-0002** — referenced as open; not written. Currently blocks the migrations item

### P2 — evidence gaps against Studio 5 objectives
Assessment is competency-based PASS/FAIL on evidence; no deployment or demo is required.

| Obj | Standing | Gap |
|---|---|---|
| 1.1 requirements + methodology | Partial | **No diagrams at all** (verified: no mermaid/drawio/puml). Rubric names ERD, UML, flowcharts, architecture diagrams. No traceability matrix. No user stories |
| 1.2 contribute to codebase | Strong | Bhanu: ~70 commits/wk, 25+ PRs, documented reviews, CI, critical-bug fixes. Keep cadence steady across the block |
| 2.1 evaluate + justify | Good | ADR-0001, ADR-0003, enterprise-stack evaluation. Missing: decision matrix, consolidated ethical/legal analysis (Privacy Act, no-invented-facts, human-reviewer rule are implemented but scattered), ADR-0002 |
| 3.1 team communication | Partial | No minutes, no stakeholder meeting records. Discussions + PR threads exist |
| 3.2 industry-standard tools | Strong | Project board (30+ items, statuses, assignees), Issues, PRs, Actions, Discussions, Dependabot, CODEOWNERS |
| 3.3 documentation | **Weakest** | No user documentation. **No reflective report** (explicitly required). No system design diagrams |

### P3 — workload balance
- Bhanu: dominant contributor. Well covered.
- Roshan: contributing (13 commits 22 Jul); has 5 assigned issues (#52–56).
- **Paras — corrected diagnosis.** An earlier note here said "no commits in 30 days". That was
  **wrong**: it ran `git log --author` against the checked-out branch, which cannot see unmerged
  branches. Verified against `--all`:
  - **7 commits, all dated 24 Jul**, on 7 pushed branches: `homepage-refresh`, `about-page`,
    `events-page`, `members-page`, `connect-page`, `trade-page`, `partners-page`.
  - **Only one PR exists (#28, homepage-refresh).** The other six branches have no PR at all, so the
    work is stranded and cannot be reviewed, merged, or counted as contribution.
  - Each branch is 1 commit ahead and roughly 39–42 commits behind `main`.
  - The `$3.68b` figure conflict is present in `homepage-refresh` **and** `trade-page`.

  The accurate problem is not "Paras did nothing". It is: **content work exists but none of it has
  landed in `main`, six branches have no PR, and the owned UI work (design system, review/approval
  UI, FTA embed, Comms review UI) has not started.** The fix is to get the six branches into PRs and
  reviewed, then get one end-to-end UI slice started — not to write him off.

### Deliberately NOT doing
Enterprise platform build (Azure/Entra/Next.js). Contradicts ratified ADR-0001, unbounded scope, no
ops team, and the rubric requires none of it. Rejection reasoning is a capstone artifact in itself —
capture it as ADR-0004.

---

## Traceability — PR to issue linking (DONE, #102 / PR #103)

The board's `Linked pull requests` column was empty on every Done item. Verified the cause rather
than assuming it: GitHub forms that link only from a closing keyword in the PR body **before** merge.
Editing a merged PR body afterwards produces a `CrossReferencedEvent`, never the `ConnectedEvent`
that makes the real link, and no GraphQL mutation exists for it. So the ~30 already-merged PRs cannot
be retrofitted — their delivery record lives in issue comments instead (#43, #38, #49, #59, #62, #69).

Fixed forward: a required `Linked issue` section in the PR template, plus a `linked-issue` CI job
that fails any PR without a keyword. The regex accepts every form GitHub itself links from —
`Closes #12`, `Closes: #12`, cross-repo `Closes owner/repo#12`, and the full issue URL — because the
first draft only matched the bare form and would have blocked valid cross-repo PRs. Issue #102
auto-closed when PR #103 merged, which is the check working end to end.

**Board is now fully populated:** 69 items, every one carrying Lane, Priority, Phase and Status.
Applying the 204 field values failed silently three times first; root cause was CRLF line endings in
the generated plan file, so every option id carried a trailing `\r` and the API correctly rejected it.
The loop also piped errors away and exited 0, reporting success for 204 consecutive failures. If a
bulk board script ever "succeeds" with nothing changed, check line endings and check exit codes.

---

## Phase 2+ — planned work (not started)

**P2 fixes:** de-duplicate controlled docs; agent repo links to `inzbc`; move backup-procedure.

**Diagrams (mermaid, in-repo, versioned):** ERD from `database/schema.sql`; system architecture
(collector → gateway → scoring → gates → brief); SIP-184 run-flow from `schemas/state-machine.md`;
sequence diagram for the scoring + verification path.

**User documentation:** SIP operator guide (open a run → record source outcomes → review candidates →
QA → CEO decision → manual send → close), written for Sunil/Paras/Roshan, not for engineers.

**Requirements formalisation:** user stories with acceptance criteria for each lane; a traceability
matrix mapping requirement → issue → PR → test.

**Ceremony records:** minutes template + backfill from the real GitHub record (Discussions, PR
threads, board changes are timestamped evidence of what was discussed and when).

**Weekly reporting:** progress report + timesheet templates, per member, due Mondays.

**Per-member PDR evidence packs:** one page each mapping objective → concrete artifact links.

---

## Notes for whoever resumes
- Do not put career ambitions or assessment-gaming language in any repo file. Frame everything as
  professional project work.
- Everything client-facing follows the repo rules: no invented statistics, sourced material only,
  `[[placeholder]]` where a fact is owed by INZBC, named human reviewer before publish.
- The reflective report and PDR worksheet must be written by the learner personally. Provide
  structure and prompts only.
