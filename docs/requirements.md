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
| NFR-03 | No AI-drafted output publishes without a named human reviewer | CLAUDE.md, SIP-050 §26 | Done (enforced by gates) |
| NFR-04 | Member and personal data handled per the NZ Privacy Act 2020 | Legal | Planned (applies once member data is stored) |
| NFR-05 | Automated, member, external and public distribution stay disabled until SIP-191 | launch-config | Done (flags default off) |
| NFR-06 | Every significant technical decision is recorded as an ADR with alternatives | SCRUM contract | In progress (ADR-0001, 0003 done; 0002 open) |
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

*Priority: Must. Status: Blocked — requires the platform backend and run configuration.*

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
- [x] A no-match response is surfaced as Action Required

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

*Source: modules/fta-centre.md. Priority: Should. Status: Planned — issue #59.*

Acceptance criteria:
- [ ] Query renders citation, effective date, next step and confidence rating
- [ ] A no-match result renders the escalation path, never a fabricated answer

---

## 4. Traceability matrix

Each requirement mapped to the issue, the pull request that delivered it, and the tests that hold it
in place. A control requirement with no test is not counted as done.

Test counts are **test functions**; parametrised tests expand to more cases at run time (for
example `test_orchestrator.py`'s 19 functions run as 32 cases).

| Req | Story | Issue | Delivered by | Implementation | Tests |
|---|---|---|---|---|---|
| REQ-G-01 | Mandatory source coverage | — (follow-up #52) | PR #27, #35, #51 | `apps/sip/collector/source_register.py` | `test_source_register.py` (14) |
| REQ-G-02 | Verification gate | — | PR #23 | `apps/sip/collector/verification.py` | `test_verification.py` (4), `test_assessment.py` (10) |
| REQ-G-03 | Human gates on lifecycle | #62 | PR #67 | `apps/sip/core/orchestrator.py` | `test_orchestrator.py` (19) |
| REQ-G-04 | Approval ≠ distribution | #62 | PR #67 | `apps/sip/core/orchestrator.py` | `test_orchestrator.py` (19) |
| REQ-I-01 | Capture before selection | — | PR #23 | `collector/mapping.py`, `ingest.py` | `test_mapping.py` (13), `test_ingest.py` (5) |
| REQ-I-02 | SIP-050 scoring | — | PR #34, #50 | `apps/sip/core/scoring.py` | `test_scoring.py` (9), `test_candidate_relevance_bounds.py` (3) |
| REQ-I-03 | Untrusted article text | #38 | PR #50 | `apps/sip/core/scoring.py` | `test_scoring_injection.py` (14) |
| REQ-I-04 | Duplicate suppression | — | PR #23 | `apps/sip/collector/dedupe.py` | `test_dedupe.py` (7) |
| REQ-I-05 | End-to-end live run | #55 | — | — | Blocked |
| REQ-F-01 | Sourced answers only | — | PR #23, #32 | `apps/fta/explainer.py`, `corpus.py` | `test_explainer.py` (11), `test_corpus.py` (7) |
| REQ-F-02 | Information Standard | — | PR #32 | `apps/fta/standards.py` | `test_explainer.py` (11) |
| REQ-U-01 | Review and QA interface | #57 | — | — | Planned |
| REQ-U-02 | CEO decision screen | #57 | — | — | Planned |
| REQ-U-03 | Accessible design system | #58 | — | — | Planned |
| REQ-U-04 | FTA Explainer embed | #59 | — | — | Planned |
| NFR-01 | Server-side model calls | #36 | PR #34 | `services/api/model_gateway.py` | `test_model_gateway.py` (2) |
| NFR-02 | Fail closed on Critical | — | PR #23, #34, #67 | across gates | `test_orchestrator.py`, `test_verification.py`, `test_scoring_injection.py` |
| NFR-08 | Controlled docs single source | — | PR #72, agent PR #12 | `docs/sip/launch/` | Verified by diff; no automated test |

**Coverage summary:** 18 requirements tracked. 13 are delivered — 12 of those with automated test
coverage, plus NFR-08 which is verified by diff rather than by a test. Five remain: four in the UX
lane (planned, issues #57–59) and REQ-I-05 blocked on the platform backend.

---

## 5. Known gaps

Recorded rather than filled with assumptions:

| Gap | Blocks | Owner |
|---|---|---|
| FTA sectors in scope and disclaimer wording | Final Explainer copy | INZBC |
| Internal platform hosting decision (ADR-0002) | Database migrations, receiver service | Platform lane |
| Redaction policy — what counts as member/Board/confidential | Redaction layer (issue #37) | INZBC, with platform lane |
| SIP-191 launch authority | Any automated distribution | INZBC |

---

## Related
- [`architecture.md`](architecture.md) — system, state machine and data model diagrams
- [`../schemas/api-contract.md`](../schemas/api-contract.md) — interface contract
- [`../schemas/state-machine.md`](../schemas/state-machine.md) — authoritative transition list
- [`sip/operator-guide.md`](sip/operator-guide.md) — user documentation for running a day
- [`decisions/`](decisions/) — architecture decision records
