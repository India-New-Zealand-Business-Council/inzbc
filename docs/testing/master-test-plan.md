# Master acceptance test plan (#210)

Phase 1 deliverable per `docs/inzbc-ai-operating-system.md` §Phase 1 and a Phase 2 gate
condition ("UAT... tests passed"). Written before the build finishes, per the programme brief's
own instruction, so acceptance is measured against something agreed in advance rather than
negotiated at the end.

**Status: DRAFT — not yet reviewed by INZBC.** Nothing here is a pass/fail decision; it is the
criteria a later decision will be measured against. `docs/testing/acceptance-register.md` is
where actual UAT sessions get logged once this plan is agreed.

## Scope: what this plan covers, and what it deliberately does not

`docs/modules/README.md` lists nine modules. Three have code today; six are `planned` with
nothing built. Writing acceptance criteria for a module that does not exist would be inventing a
test for vapor — the opposite of what an acceptance plan is for. This plan covers exactly the
three built modules, and is extended as each further module reaches `build` status.

| Module | Status | In this plan |
|---|---|---|
| 7. SIP (Strategic Intelligence Platform) | `launch` | Yes — §1 |
| 6. FTA Implementation Centre | `spec`, but the Explainer + corpus are built and deployed | Yes — §2 |
| 8. AI Communications Assistant | `planned`, but the service side is built (draft generation + persistence + approval) | Yes — §3 |
| 1, 2, 3, 4, 5, 9 | `planned`, no code | Not yet — nothing to accept |

## Who signs

Per the Phase 1 gate: **INZBC Executive Sponsor, Finance Owner, Privacy Owner and Technical Lead.**

**Open as of this writing:** the Finance Owner and Privacy Owner for the Phase 1 gate are named
in `docs/client-answers-relayed-2026-08-09.md`'s open-items table (item 11) as still needed from
Sunil. The gate cannot be signed until they are named, independent of whether the tests
themselves pass — this plan does not assume an answer to that.

## §1 SIP — acceptance criteria

Sourced from `docs/sip/README.md`'s stated pre-use requirements and `docs/sip/launch/SIP-188_qa_checklist_v0.9.md`'s per-run criteria, not invented fresh — SIP already has an operational QA
checklist; this plan sits one level above it (does the *system* meet the bar, not does *one run*).

**Preconditions before UAT can run at all** (tracked as blockers, not test failures):
- [ ] SIP-191 authorised run window — expired 31 Jul 2026, no continuation without a fresh
  controlled decision (`docs/sip/launch/launch-config.md`). A dry run (PR #264) proves the code
  path; UAT needs a real authorised run to exercise, not a dry run.
- [ ] Named SIP staff users (1-2, per `docs/client-answers-relayed-2026-08-09.md`) — without
  names, roles cannot be seeded and the separation-of-duties criteria below cannot be exercised
  by real distinct people.
- [ ] #40 (SIP adversarial security review) — `docs/sip/README.md` makes this non-negotiable
  before any staff use; UAT is a form of use.

**Acceptance criteria, once preconditions clear:**
- [ ] A full SIP-184 daily run completes: collection → capture → assessment → QA → CEO decision
  → (no) distribution, against a real authorised window.
- [ ] Every mandatory SIP-185 source has a recorded outcome; none silently blank (SIP-188).
- [ ] Separation of duties holds in practice: the analyst who captured a candidate cannot also
  verify it (BR8) — exercised by a real second person, not just the code-level test.
- [ ] The QA reviewer independently fails a run with a Critical defect, and the run is correctly
  blocked from CEO decision (REQ-U-01).
- [ ] `production_enabled` stays false until #189 (close out controlled launch) is recorded.
- [ ] Audit trail for the run is complete and readable by an Auditor-role account
  (`GET /api/runs/{id}/audit`).
- [ ] No automated distribution occurs at any point (`SIP_AUTOMATED_DISTRIBUTION_ENABLED`
  defaults false, locked by `daily-india-nz-news-agent`'s `test_distribution_gate.py`).

## §2 FTA Implementation Centre — acceptance criteria

Sourced from `docs/modules/fta-centre.md` and the Explainer's own guarantees.

- [ ] A query with a confirmed corpus match returns a sourced answer: citation, verified date,
  in-force status, disclaimer — never a bare number with no source.
- [ ] A query with no confirmed match returns Action Required (escalate to INZBC), never a
  guess or a fabricated figure.
- [ ] No answer states a tariff line, percentage, or in-force date not traceable to a Tier-1
  source in `docs/fta-source-corpus.md`.
- [ ] The FTA UI is usable at 320px width (Playwright coverage, #100).

## §3 AI Communications Assistant — acceptance criteria

Sourced from `docs/modules/comms-assistant.md`'s Definition of Done, status as recorded there
14 Aug 2026.

- [ ] A generated draft is never distributed automatically — no send/publish path exists in
  the codebase (holds by construction, verified by absence rather than by a control that could
  be bypassed).
- [ ] The draft's own author cannot approve it (BR8) — `refuse_self_review`, tested against a
  real Postgres.
- [ ] Every draft creation and every approval is an audited, attributable event.
- [ ] **Not yet testable:** the reviewer UI (#60) does not exist, so a human reviewer's actual
  workflow cannot be exercised end to end yet — this criterion moves to "ready" once #60 lands.
- [ ] **Not yet testable:** the free-text brief's prohibited-data handling (#303, the "live gap"
  in `docs/api-integration-spec.md`) has no structural control yet, so there is nothing to test
  against beyond the operator being told not to paste member details.

## Test levels, and where each already lives

Not duplicating engineering test suites here — this plan is the acceptance layer above them.

| Level | Who exercises it | Where |
|---|---|---|
| Unit / integration | Engineers | `pytest`, `pnpm test` — CI on every PR |
| Per-run QA | Reviewer (Paras primary, Roshan backup) | SIP-188 checklist, per run |
| System acceptance (this plan) | INZBC | `docs/testing/acceptance-register.md`, once preconditions clear |
| Production approval | Executive Sponsor | #189, separate from acceptance passing |

## Next steps

1. This plan needs INZBC review before it counts as "agreed in advance" rather than a draft.
2. SIP UAT cannot be scheduled until its three preconditions above clear.
3. FTA UAT can be scheduled now — nothing blocks it.
4. Comms UAT is partial until #60 exists.
