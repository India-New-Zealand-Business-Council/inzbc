# Studio 6 plan, Bhanu Gupta

Block 4 2026, 5 Oct to 4 Dec. Role: tech lead, foundation, security and integration (lanes in
[bhanu.md](bhanu.md)). This file is the dated copy of the personal plan. Every log below is kept
here so git dates each entry. Prepared with AI assistance; the measurements are reproducible from
the commands given, and the reflective entries are left for me to write in my own words.

## Research component

**Safe agent coordination: an AI coordinator that can't bypass human approval.**

**Research question.** Can an AI agent run the daily intelligence process while hard-coded
controls guarantee it never skips a human approval step?

| Part | Where |
|---|---|
| Literature review, 17 sources, annotated, APA 7 | [agent-safety-literature-review.md](../research/agent-safety-literature-review.md) |
| Baseline measurements | [agent-safety-baseline.md](../research/agent-safety-baseline.md) |
| Solution domain: techniques used and why | [agent-safety-solution-domain.md](../research/agent-safety-solution-domain.md) |
| Harnesses and committed results | `apps/sip/core/eval/`, pinned by `apps/sip/core/tests/test_research_eval.py` |

## What I built

| Build | Merged |
|---|---|
| Coordinator agent with 7 allowed tools and audit replay (#62) | 16 Oct |
| Embeddings and pgvector semantic retrieval (#63) | 16 Oct |
| AI quality judge for briefs, with a golden test set (#64) | 16 Oct |
| Streaming drafts for the Comms Assistant (#65) | 16 Oct |
| Run engine, decision records, audit log, model gateway | Earlier |

## Key dates

| What | When |
|---|---|
| Practice PDR | Week 5, 2 to 6 Nov |
| All final evidence ready | Fri 20 Nov |
| Final PDR meeting | Week 8, 23 to 27 Nov |
| Moodle submission | Fri 27 Nov, 10:30 AM |
| Handover | Week 9, 30 Nov to 4 Dec |

## Timeline

| Week | Focus | Items |
|---|---|---|
| W1, 5 Oct | Kick off and plan | Confirm PDR slots. Kickoff. Agree lanes and the review policy |
| W2, 12 Oct | Build the AI pieces | #62 coordinator, #63 embeddings, #64 quality judge, #65 streaming drafts. All merged 16 Oct |
| W3, 19 Oct | Baseline and reading | Gate-safety, replay and tamper baselines measured (24 Oct). Literature review drafted (24 Oct). Solution domain written. This plan committed |
| W4, 26 Oct | Close the baseline | Judge vs human: live judge run and blind labels from a QA reviewer. Practice PDR worksheet. Confirm the practice slot |
| W5, 2 Nov | Practice PDR | Present the question, baseline and planned change. Log feedback the same day |
| W6, 9 Nov | Make the change | Sign each human decision when it is recorded, and hash-chain the agent audit log (the forged-decision gap) |
| W7, 16 Nov | Measure the change | Re-run all three harnesses, before vs after. Evidence ready 20 Nov |
| W8, 23 Nov | Final PDR | Rehearse. Final PDR. Moodle upload. Log comments |
| W9, 30 Nov | Handover | Hand over open items. Close or reassign issues |

## Baseline, 24 Oct 2026

| Measurement | Baseline | Target | After the W6 change |
|---|---|---|---|
| Gate-safety attacks blocked | **48/48 (100%)** | 100% | 48/48 |
| Control knockouts that let their own attacks through | **4/4** | 4/4 (proves the suite can fail) | 4/4 |
| Runs replayed exactly from the audit log | **200/200** | 200/200 | 200/200 |
| Runs re-executed to an identical log | **200/200** | 200/200 | 200/200 |
| Safety-relevant tampering detected | **2396/2596 (92.3%)** | 100% | **3196/3196 (100%)** |
| Forged human decision detected | **0/200** | 200/200 | **200/200** |
| Metadata-only tampering detected | 0/1000 | Not a target | 1000/1000 |
| Judge vs golden-set verdicts | Not run (no model credentials) | Report with kappa | Not affected by the change |
| Judge vs human QA reviewer | Not measured (no reviewer labels yet) | Report with kappa | Not affected by the change |

What the baseline shows: the agent cannot cross a human gate. 48 of 48 attempts fail, and each
control is proven necessary by its knockout. The audit artefact has a weakness the agent does not.
Someone with write access to stored logs could forge a human approval that replay accepts. At
baseline that was held off by database privileges (INSERT and SELECT only), not by the log itself.
The W6 change, made early on 24 Oct, signs each human decision and seals the agent log. The "After"
column comes from the same harness, seed and runs (baseline doc, section 5).

## Issues

| Issue | Status | Note |
|---|---|---|
| #62 coordinator agent | Done, 16 Oct | Baseline measured 24 Oct |
| #63 embeddings | Done, 16 Oct | Advisory capability; no production ranker change authorised |
| #64 quality judge | Done, 16 Oct | Advisory only. Agreement with a human reviewer not yet measured |
| #65 streaming drafts | Done, 16 Oct | Named-reviewer gate unchanged |
| #344 source outcomes | Decision recorded 24 Oct | Option A, analyst-confirmed manual outcomes. #446 merged |
| #55 first production run | **Blocked on INZBC** | Needs a renewed SIP-191 authorisation and an approved PAT. Client's dependency, not engineering |
| #189 launch approval | **Blocked on INZBC** | Production launch approval outstanding. Client's decision |
| #303 written residual-risk acceptance | Waiting on INZBC | Verbal acceptance reported; written condition not yet met |
| #45 site forms | Receiver merged (#433) | Form types, routing, retention and privacy notice are client decisions |

## Status report lines (client-owned delays)

Keep these in every status report until they move, so the delay stays recorded as the client's:

- **#55 first production run:** blocked on INZBC renewing the SIP-191 authorisation and supplying
  an approved PAT. The engineering path is ready, and #446 adds the analyst-confirmed source
  checks.
- **#189 launch approval:** production launch approval is outstanding from INZBC. Production and
  automated distribution stay disabled until it is given.

## Evidence checklist

| Done | Week | Evidence | Obj |
|---|---|---|---|
| [x] | W2 | #62 to #65 merged (16 Oct) | 2.2 |
| [x] | W3 | Gate-safety baseline, 48/48, with control knockouts (24 Oct) | 2.2 |
| [x] | W3 | Replay and tamper baseline, 200 runs (24 Oct) | 2.2 |
| [x] | W3 | Literature review, 17 sources checked against their records (24 Oct) | 2.1 |
| [x] | W3 | Solution domain written (24 Oct) | 2.1 |
| [x] | W3 | #344 decision recorded on the issue (24 Oct) | 3.1 |
| [ ] | W4 | Judge vs golden set, live run | 2.2 |
| [ ] | W4 | Blind QA reviewer labels for the 8 golden cases, then judge vs human | 2.2 |
| [ ] | W4 | Practice PDR worksheet | PDR |
| [ ] | W5 | Practice PDR feedback written down | PDR |
| [x] | W6 | Signed human decisions and hash-chained audit log (brought forward, 24 Oct) | 2.2 |
| [ ] | W7 | Before vs after table for all three harnesses (gate safety and replay done 24 Oct; judge waits on W4) | 2.2 |
| [ ] | W7 | Reflective report, evidence index and final worksheet ready by Fri 20 Nov | PDR |
| [ ] | W8 | Final PDR attended, Moodle upload done, feedback logged | PDR |

## Plan change log

| Date | Change | Why |
|---|---|---|
| 2026-10-24 | W6 change set: signed human decisions and a hash-chained audit log | The replay baseline found a forged human decision is accepted (0/200 detected). This is the change with the most direct link to the research question |
| 2026-10-24 | W6 change brought forward from 9 Nov | It needed no client input and the harness was ready. W6 and W7 now cover the judge measurements if W4 slips |
| 2026-10-24 | Judge vs human split into two measurements | The golden labels are the rubric author's synthetic test labels, not a QA reviewer's decisions. Agreement with an independent reviewer has to be measured separately |

## Stakeholder and mentor feedback log

| Date | From | Feedback received | What I changed because of it | Evidence link |
|---|---|---|---|---|
| | | | | |

## Daily log

| Date | Done today (PRs, issues, reviews) | Blocked or waiting on | Tomorrow |
|---|---|---|---|
| Fri 23 Oct | Reviewed and merged #433 to #446 and inzview #9 and #10. Fixed the review findings left on each, including a CI failure on #433. Closed inzview #8 | INZBC: #55, #189, sector graphics for the FTA Centre | Measure the agent baseline |
| Sat 24 Oct | Recorded the #344 decision. Gate-safety, replay and tamper baselines measured. Literature review, solution domain and this plan written. Signed decisions and the sealed agent log built and re-measured | Model credentials and a QA reviewer for judge vs human | Run the live judge, ask for blind labels |

## Weekly journal

### Week 3, 19 to 23 Oct

**Planned vs what happened.** [My own words.]

**What helped or got in the way.** [My own words.]

**What I will change.** [My own words.]
