# Requirements

How requirements are captured for the INZBC platform, the user stories they turn into, and the
traceability matrix linking each one to the code and tests that satisfy it.

---

## 1. Method

Work is run as Scrum against a groomed backlog in GitHub Projects. Requirements arrive from three
places and are handled differently depending on the source:

| Source | Type | Handling |
|---|---|---|
| Approved INZBC control documents (SIP-050 v1.1, SIP-184/185/186/188, launch-config) | Mandatory, externally controlled | Transcribed, never reinterpreted. Where code enforces one, the code cites the clause |
| Module specifications in [`modules/`](modules/) and [`page-specs.md`](page-specs.md) | Functional | Broken into user stories with acceptance criteria |
| Client requests and discovery ([`discovery.md`](discovery.md), [`sunil-requests.md`](sunil-requests.md)) | Functional and commercial | Confirmed with the client before a story is written |

Three rules govern what may become a requirement:

1. **No requirement is invented to fill a gap.** Where a business rule is undecided, the story stays
   blocked and the gap is recorded — it is not filled with an assumption.
2. **Facts owed by INZBC are marked `[[placeholder]]`** rather than guessed.
3. **A control requirement is only "done" when it is enforced in code and covered by a test.** A
   control that exists only in a document is a documented intention, not a control.

**Priority** uses MoSCoW. **Status** is one of: `Done` (merged and tested), `In progress`,
`Blocked` (waiting on a decision or dependency), `Planned`.

---

## 2. Non-functional requirements

These constrain every story and are drawn from the SIP non-negotiables and NZ law.

| ID | Requirement | Source | Status |
|---|---|---|---|
| NFR-01 | All model calls happen server-side; provider keys never reach a browser | SIP spec non-negotiables | Done |
| NFR-02 | Any Critical condition fails closed — it is never downgraded to a warning | SIP-184 fail-closed list | Done |
| NFR-03 | No AI-drafted output publishes without a named human reviewer | PROJECT-RULES.md, SIP-050 §26 | Done (enforced by gates) |
| NFR-04 | Member and personal data handled per the NZ Privacy Act 2020 | Legal | Planned (applies once member data is stored) |
| NFR-05 | Automated, member, external and public distribution stay disabled until SIP-191 | launch-config | Done (flags default off) |
| NFR-06 | Every significant technical decision is recorded as an ADR with alternatives | SCRUM contract | In progress (ADR-0001–0004 recorded; standing practice, not a one-off) |
| NFR-07 | Work lands via reviewed pull request; CI green; no direct pushes to `main` | CONTRIBUTING.md | Done |
| NFR-08 | Controlled documents exist in exactly one location | SIP control model | Done |

---

## 3. User stories

### 3.1 Governance and control (platform lane)

**REQ-G-01 — Mandatory source coverage**
> As the **Quality Reviewer**, I need every applicable mandatory source to carry a recorded outcome,
> so that a run cannot pass QA with an unexplained gap in coverage.

*Source: SIP-184 §4, SIP-185. Priority: Must. Status: Done.*

Acceptance criteria:
- [x] Every mandatory source in the SIP-185 register must have an outcome before QA can pass
- [x] A missing outcome is reported as a Critical stop, not a warning
- [x] Outcomes are restricted to the six controlled codes
- [x] Sources are identified by their SIP-185 code, not by name (names are not unique across
      jurisdictions, which would silently under-count coverage)

**REQ-G-02 — Verification gate on High and Critical claims**
> As the **CEO**, I need High and Critical claims to be refused unless they carry official or
> high-confidence verification, so that the brief never asserts something serious on weak evidence.

*Source: SIP-050 §14 and §27, SIP-184 §7. Priority: Must. Status: Done.*

Acceptance criteria:
- [x] A High or Critical signal with verification `Unverified`, `Rejected` or unknown is refused
- [x] `Not Required` is also refused for High/Critical — it is self-contradictory at that level
- [x] An unknown verification state is treated as unverified (fail closed), never assumed safe
- [x] Low and Medium signals are unaffected

**REQ-G-03 — Human gates on the run lifecycle**
> As the **CEO**, I need authority, QA, my decision and the send step to require a recorded human
> action, so that no automated component can advance the run past a control point on its own.

*Source: SIP-184 §1/§11/§12/§13, schemas/state-machine.md. Priority: Must. Status: Done.*

Acceptance criteria:
- [x] Only transitions listed in the state machine are permitted; anything else is refused
- [x] Gated transitions require a recorded decision naming an approver
- [x] A decision with a blank approver or blank decision cannot satisfy a gate
- [x] A stopped run is terminal and cannot be resumed under the same run id
- [x] Every accepted transition appends to an append-only history that can be replayed

**REQ-G-04 — Approval and distribution are separate decisions**
> As the **CEO**, I need approving the report and authorising its distribution to be two distinct
> recorded decisions, so that approval alone never causes something to be sent.

*Source: SIP-050 §26, SIP-184 §12–13, launch-config. Priority: Must. Status: Done.*

Acceptance criteria:
- [x] Report approval does not imply distribution authority
- [x] Distribution requires its own recorded authorisation
- [x] No automatic send path exists during the controlled launch

### 3.2 Intelligence pipeline (intelligence and data lane)

**REQ-I-01 — Capture candidates before selection**
> As the **Analyst**, I need every potentially relevant item captured before any filtering, so that
> relevant material is not lost through premature judgement.

*Source: SIP-184 §5. Priority: Must. Status: Done.*

Acceptance criteria:
- [x] Collection-engine output maps to candidate records with source, times, headline, summary, URL
- [x] Capture records raw material only — no scoring or routing decisions at this stage
- [x] One malformed item does not abort the batch; it is recorded as a failure and the rest proceed
- [x] An unparseable publication time is recorded as absent rather than guessed

**REQ-I-02 — Scoring against the approved framework**
> As the **Analyst**, I need relevance, signal and confidence computed against SIP-050, so that
> assessment is consistent between runs and between analysts.

*Source: SIP-050 §11–13. Priority: Must. Status: Done.*

Acceptance criteria:
- [x] Relevance scores are integers 0–5 and are rejected outside that range
- [x] Signal and confidence accept only the controlled vocabulary
- [x] Model output that does not match the contract is rejected — the candidate stays unscored
      rather than receiving assumed values
- [x] The scorer recommends; verification remains human-owned and is never model-assigned

**REQ-I-03 — Article text is untrusted input**
> As the **platform owner**, I need article content treated as untrusted, so that text in a source
> cannot alter how the system scores or what it returns.

*Source: SIP-050 §14 (no inference into fact); standard practice for model inputs. Priority: Must.
Status: Done.*

Acceptance criteria:
- [x] Hostile article text cannot corrupt the prompt structure
- [x] Injected instructions cannot force an out-of-range score
- [x] Extra fields, prose, fenced payloads, wrong types and duplicate keys are all rejected
- [x] A hostile article with a well-formed model response still scores normally (no over-blocking)

**REQ-I-04 — Duplicate suppression across runs**
> As the **Analyst**, I need repeat coverage of the same development identified, so the brief does
> not report one story twice.

*Source: SIP-050 §17, SIP-184 §6. Priority: Should. Status: Done.*

Acceptance criteria:
- [x] Matches on normalised URL first, then normalised headline
- [x] Works across separate runs, not only within a single fetch

**REQ-I-05 — End-to-end live run**
> As the **Analyst**, I need the pipeline to run end to end against the SIP-184 SOP, so the controls
> are proven against real material rather than fixtures.

*Source: SIP-184 §1-7 (the intelligence-pipeline steps; §8-14 are the control-plane/QA lane, out
of scope here). Priority: Must. Status: Blocked — requires the platform backend (#117, #120, #121)
and org-repo collection-engine secrets before this can run against anything but fakes.*

Acceptance criteria:
- [ ] A run opens against a real (not stub) `/api/runs` with an authorised version and a locked
      24h Pacific/Auckland coverage window, previous day 07:00 to current day 07:00 (SIP-184 §1-2)
- [ ] Every applicable mandatory source from the SIP-185 worklist has a recorded outcome before
      the run is treated as complete; a blank mandatory-source outcome blocks it (SIP-184 §3-4) —
      unit- and integration-tested against the real 112-source register already; this criterion
      is "against a live run", not fixtures
- [ ] `in_coverage_window` is computed against the run's actual locked window, not the collection
      agent's rolling filter — closes the known simplification documented in `mapping.map_article`
- [ ] Every candidate the collection engine returns is captured with full fields; one malformed
      item does not abort the batch (SIP-184 §5) — same, against a live run rather than fixtures
- [ ] Relevance/signal/confidence are computed against SIP-050 before any candidate reaches
      verification (SIP-184 §6-7) — depends on Bhanu's model gateway serving scoring (SHARED-OK,
      tracked on his worklog)
- [ ] The verification gate blocks any unverified High/Critical assessment during the live run,
      not only in tests against a fake client
- [ ] Written state is queryable afterward through the real API (`source_checks`, `candidates`),
      not only written and never read back — proves persistence, not just a successful POST

### 3.3 FTA Opportunity Explainer

**REQ-F-01 — Sourced answers only**
> As an **INZBC member**, I need answers drawn only from verified sources with citations, so I can
> rely on them for commercial decisions.

*Source: modules/fta-centre.md, docs/fta-source-corpus.md. Priority: Must. Status: Done.*

Acceptance criteria:
- [x] Every answer carries its citation, effective/verified date and jurisdiction
- [x] Unconfirmed corpus entries are never surfaced to a member
- [x] A query with no confirmed match returns nothing and routes the member to INZBC
- [x] Answers state that the FTA is signed but not yet in force
- [x] No model call is involved, so no answer can be fabricated

**REQ-F-02 — Information Standard on every answer**
> As the **CEO**, I need each answer to carry the approved INZBC disclaimer and a confidence rating,
> so members understand the standing of what they are reading.

*Source: docs/information-standard.md (approved wording). Priority: Must. Status: Done.*

Acceptance criteria:
- [x] The approved AI Information Standard text appears on every answer
- [x] A confidence rating is derived from the cited source's tier
- [x] A no-match response is surfaced to the member as Action Required — `answer_query` returns
      `[]`, and `apps/fta/ui/src/components/FtaQuery.tsx` renders the resulting `NO_MATCH_CONFIDENCE`
      state via `ActionRequired`, covered by `FtaQuery.test.tsx` (escalation state, no citation or
      verified date shown, announced in a live region). Found stale during adversarial review of
      the project charter (#215); closed as #218.

### 3.4 Review and approval interface (product and UX lane)

**REQ-U-01 — Brief review and QA interface**
> As the **Quality Reviewer**, I need to work the SIP-188 checklist against the drafted brief in one
> place, so QA is consistent and its result is recorded.

*Source: SIP-188, modules/dashboards.md. Priority: Must. Status: Planned — issue #57.*

Acceptance criteria:
- [ ] The QA checklist is presented item by item against the brief
- [ ] A Critical failure blocks progression to the CEO decision
- [ ] The reviewer is recorded and cannot be the run's analyst
- [ ] Illegal state transitions are disabled in the interface, mirroring the state machine, with the
      server remaining the authority

**REQ-U-02 — CEO decision screen**
> As the **CEO**, I need to record my decision and, separately, distribution authorisation, so that
> both are captured with reason, timestamp and version.

*Source: SIP-184 §12. Priority: Must. Status: Planned — issue #57.*

Acceptance criteria:
- [ ] One decision recorded from: Continue, Continue with Correction, Pause, Stop
- [ ] Distribution authorised Yes/No captured as a separate action
- [ ] Reason, conditions, owner, evidence reference and next review captured
- [ ] Nothing can be sent from this screen without distribution authorisation

**REQ-U-03 — Accessible design system**
> As a **member or staff user**, I need the interface to meet WCAG 2.2 AA, so the platform is usable
> regardless of ability.

*Source: modules/website.md, ADR-0003. Priority: Must. Status: Planned — issue #58.*

Acceptance criteria:
- [ ] Components are token-driven so brand tokens swap in one change
- [ ] Focus order, contrast and keyboard paths are built into each component
- [ ] An end-to-end WCAG 2.2 AA audit passes on every public page

**REQ-U-04 — FTA Explainer embed**
> As an **INZBC member**, I need to ask an FTA question on the website and see a sourced answer.

*Source: modules/fta-centre.md. Priority: Should. Status: In progress — implemented locally
(PRs #85–#87, #89, #91); closure pending deployed website integration and Playwright evidence,
since the story is a member asking the question on the website. Issue #59.*

Acceptance criteria:
- [ ] Query renders citation, effective date, next step and confidence rating
- [ ] A no-match result renders the escalation path, never a fabricated answer

---

## 4. Traceability matrix

Each requirement mapped to the issue, the pull request that delivered it, and the tests that hold it
in place. A control requirement with no test is not counted as done.

Test counts are given as **`N fn / M cases`** — test functions, then the cases pytest collects
after parametrisation.

Both units are recorded because giving one invited the other. The final traceability pass (#136)
found three rows carrying case counts under a heading that said functions — `test_verification`
read 17 when it has 4 functions and 17 cases, and `test_orchestrator` and `test_runs_api` had the
same substitution. Nothing was wrong with the tests; the column was ambiguous, so it drifted.

Counts verified against `pytest --collect-only`, not read off the files, on 20 August 2026.

**Where a control is enforced matters as much as that it exists**, so the implementation column
names the durable boundary and not only the first place the rule was written. Three rows were wrong
on exactly that point and are corrected: human gates were attributed to the in-memory orchestrator
alone, which was found not to be the boundary at all, because nothing reaching the database went
through it. The gate is enforced in `persistence.apply_transition` against append-only authority
records; the orchestrator holds the same rules for the in-process path.

| Req | Story | Issue | Delivered by | Implementation | Tests |
|---|---|---|---|---|---|
| REQ-G-01 | Mandatory source coverage | — (follow-up #52) | PR #27, #35, #51 | `apps/sip/collector/source_register.py` | `test_source_register.py` (17 fn / 25 cases) |
| REQ-G-02 | Verification gate | — | PR #23, #285 | `apps/sip/collector/verification.py`, `services/api/candidate_persistence.py` | `test_verification.py` (4 fn / 17 cases), `test_candidate_persistence.py` (28 fn / 28 cases) |
| REQ-G-03 | Human gates on lifecycle | #62 | PR #67, #228, #301 | `apps/sip/core/orchestrator.py`, `services/api/persistence.py`, `database/schema.sql` (`run_authorisations`) | `test_orchestrator.py` (31 fn / 44 cases), `test_persistence.py` (17 fn / 17 cases) |
| REQ-G-04 | Approval ≠ distribution | #62 | PR #67, #285 | `apps/sip/core/orchestrator.py`, `services/api/runs.py` (`/stop`, `/fail-qa`) | `test_orchestrator.py` (31 fn / 44 cases), `test_runs_api.py` (19 fn / 29 cases) |
| REQ-I-01 | Capture before selection | — | PR #23 | `apps/sip/collector/mapping.py`, `apps/sip/collector/ingest.py` | `test_mapping.py` (16 fn / 16 cases), `test_ingest.py` (5 fn / 6 cases) |
| REQ-I-02 | SIP-050 scoring | — | PR #34, #50 | `apps/sip/core/scoring.py` | `test_scoring.py` (9 fn / 9 cases), `test_candidate_relevance_bounds.py` (3 fn / 19 cases) |
| REQ-I-03 | Untrusted article text | #38 | PR #50 | `apps/sip/core/scoring.py` | `test_scoring_injection.py` (14 fn / 27 cases) |
| REQ-I-04 | Duplicate suppression | — | PR #23 | `apps/sip/collector/dedupe.py` | `test_dedupe.py` (7 fn / 7 cases) |
| REQ-I-05 | End-to-end live run | #55 | — | — | Blocked |
| REQ-F-01 | Sourced answers only | — | PR #23, #32 | `apps/fta/explainer.py`, `corpus.py` | `test_explainer.py` (21 fn / 21 cases), `test_corpus.py` (16 fn / 16 cases) |
| REQ-F-02 | Information Standard | — | PR #32, #218 | `apps/fta/standards.py`, `apps/fta/ui/src/components/FtaQuery.tsx` | `test_explainer.py` (21 fn / 21 cases), `FtaQuery.test.tsx` |
| REQ-U-01 | Review and QA interface | #57, #263 | PR #285 (backend only) | `services/api/runs.py` (`/fail-qa`) | `test_runs_api.py` (19 fn / 29 cases). **Interface not built** |
| REQ-U-02 | CEO decision screen | #57 | PR #237, #285, #311 (backend only) | `services/api/runs.py` (`/pause`, `/stop`), `services/api/reports.py` | `test_runs_api.py` (19 fn / 29 cases), `test_reports_api.py` (24 fn / 33 cases). **Screen not built** |
| REQ-U-03 | Accessible design system | #58 | — | — | Planned |
| REQ-U-04 | FTA Explainer embed | #59 | #85–#87, #89, #91 | `apps/fta/ui`, `services/api/main.py` | `FtaQuery.test.tsx`, `test_main.py`. Built and served from the container image; **not deployed** (#99) |
| NFR-01 | Server-side model calls | #36 | PR #34 | `services/api/model_gateway.py` | `test_model_gateway.py` (2 fn / 2 cases) |
| NFR-02 | Fail closed on Critical | — | PR #23, #34, #67 | across gates | `test_orchestrator.py` (31 fn / 44 cases), `test_verification.py` (4 fn / 17 cases), `test_scoring_injection.py` |
| NFR-03 | Named human reviewer before publication | #53 | PR #162, #301 | `apps/comms/draft.py` (refuses the draft's own author), `services/api/persistence.py` (`run_authorisations`) | `test_draft.py`, `test_persistence.py` (17 fn / 17 cases) |
| NFR-04 | Privacy Act 2020 handling | #132 | — | `docs/privacy-assessment.md` | **Not testable yet** — no member data is stored (#198, #201) |
| NFR-05 | Distribution disabled until SIP-191 | — | PR #164, #237 | `database/schema.sql` (`runs.production_enabled` default false), `apps/sip/pipeline/client.py` (server-only field) | `test_models.py`, `test_client.py` |
| NFR-06 | ADR per significant decision | — | across PRs | `docs/decisions/` (7 ADRs) | Verified by review; no automated test |
| NFR-07 | Reviewed PR, green CI, no direct pushes to `main` | — | — | `.github/workflows/ci.yml` (9 jobs), `CONTRIBUTING.md` | Enforced by CI and branch protection, not by a unit test |
| NFR-08 | Controlled docs single source | — | PR #72, agent PR #12 | `docs/sip/launch/` | Verified by diff; no automated test |

**Coverage summary:** 23 requirements tracked after the final pass added the five missing NFRs
(was 18). 15 delivered with automated test coverage; NFR-06, NFR-07 and NFR-08 are enforced by
review, CI and branch protection rather than by a unit test, and say so rather than claiming a
test that does not exist.

Five remain, and they are not all the same kind of incomplete. REQ-U-01 and REQ-U-02 have their
**backends built and tested** and no interface; the requirement is written about a screen, so they
are not counted as delivered, and the row says which half exists rather than implying either
extreme. REQ-U-03 is unstarted. REQ-U-04 is built and served from the container image but not
deployed anywhere (#99). REQ-I-05 needs a live run against real sources (#55).

### Final traceability pass, 20 August 2026 (#136)

Every row was checked against the repository rather than against the previous version of this
table. Three findings, none of which changed a delivered/not-delivered verdict:

1. **Nine test counts were wrong**, and in two different ways. Six were simply stale — tests were
   added and the table was not updated. Three were the *right number in the wrong unit*:
   `test_verification` read 17, which is its case count, not its 4 functions; `test_orchestrator`
   and `test_runs_api` had the same substitution. The column now records both units so the
   ambiguity that produced this cannot recur. No tests were deleted — that was checked first,
   because a falling count is the one that would matter.
2. **Five non-functional requirements were absent from the matrix.** §2 defines eight; only
   NFR-01, NFR-02 and NFR-08 were traced. NFR-03 to NFR-07 are now rowed with honest evidence:
   two are enforced by mechanisms that are not unit tests (CI and branch protection for NFR-07,
   review discipline for NFR-06), and NFR-04 is not testable at all yet because no member data is
   stored.
3. **Nothing was marked delivered to improve the count.** REQ-U-01 and REQ-U-02 still have
   backends built and tested with no interface, and stay uncounted. REQ-I-05 is still blocked on a
   live run. REQ-U-04 is still built-but-undeployed.

Counts verified with `pytest --collect-only`. The suite stands at 1,025 passing, 0 skipped.

The earlier correction pass, which moved REQ-U-01 and REQ-U-02 from "Planned" to "backend only",
also did not count them — that was the point of it.

Every `[x]` in this document means the behaviour is implemented **and** exercised by a test. Where a
criterion depends on a caller that does not exist yet, it is left unticked even if the supporting
constant or function is present — a defined constant is not a delivered behaviour.

---

## 5. Known gaps

Recorded rather than filled with assumptions:

| Gap | Blocks | Owner |
|---|---|---|
| ~~FTA sectors in scope~~ — resolved 9 Aug 2026 by scope, not a single list (#219, `docs/client-answers-relayed-2026-08-09.md`); goods sectors build now, tourism/education/investment sourced next | ~~Final Explainer copy~~ — unblocked | Team |
| ~~FTA disclaimer wording~~ — approved by Sunil Kaushal (CEO), 24 Jul 2026; live in `apps/fta/standards.py`'s `AI_INFORMATION_STANDARD` | ~~Final Explainer copy~~ — unblocked | — |
| ~~Internal platform hosting decision~~ — closed by ADR-0002, graduated to option B by ADR-0004 | ~~Database migrations, receiver service~~ — unblocked | Platform lane |
| Redaction policy — what counts as member/Board/confidential | Redaction layer (issue #37) | INZBC, with platform lane |
| SIP-191 launch authority | Any automated distribution | INZBC |

---

## Related
- [`architecture.md`](architecture.md) — system, state machine and data model diagrams
- [`../schemas/api-contract.md`](../schemas/api-contract.md) — interface contract
- [`../schemas/state-machine.md`](../schemas/state-machine.md) — authoritative transition list
- [`sip/operator-guide.md`](sip/operator-guide.md) — user documentation for running a day
- [`decisions/`](decisions/) — architecture decision records
