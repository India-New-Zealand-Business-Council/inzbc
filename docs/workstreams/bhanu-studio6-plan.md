# Studio 6 plan, Bhanu Gupta

Block 4 2026, 5 Oct to 4 Dec. Role: tech lead, foundation, security and integration (lanes in
[bhanu.md](bhanu.md)). This file is the dated copy of the personal plan. Every log below is kept
here so git dates each entry. Prepared with AI assistance; the measurements are reproducible from
the commands given, and the reflection paragraphs are evidence-based drafts for me to personalise and confirm before
assessment. Unreceived feedback and future-week measurements remain unfilled.

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
| Coordinator agent run from the app: sealed, re-verified rehearsals on Run Detail | 24 Oct (stacked on the W6 change) |
| Role-aware Getting Started walkthrough in the platform shell | 24 Oct |
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
| Judge vs golden-set verdicts | **8/8 agree, kappa 1.0** (17/17 score bounds met; `gpt-4.1-mini`, 24 Oct) | Report with kappa | Not affected by the change |
| Judge vs human QA reviewer | Not measured (no reviewer labels yet) | Report with kappa | Not affected by the change |
| Real model under planted instructions (section 6) | Not measured | 0 breaches | **0 breaches in 35 runs**; planner attempts 2/30 hostile runs, scorer obeyed 5/5 "score Critical" and was refused |
| Database-level rewrites caught on read (section 7) | 341/759 without the key | 100% | **759/759 with the key** |

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
| #64 quality judge | Done, 16 Oct | Advisory only. Agrees with the golden set 8/8 (kappa 1.0, 24 Oct). Agreement with a human reviewer not yet measured |
| #65 streaming drafts | Done, 16 Oct | Named-reviewer gate unchanged |
| #344 source outcomes | Decision recorded 24 Oct | Option A, analyst-confirmed manual outcomes. #446 merged |
| #55 first production run | **Open, checked 30 Oct** | SIP-191 authorisation and PAT reported in place on 24 Oct. Latest issue handoff still requires the safe transactional/idempotent batch-import path, original authority, live source outcomes and actual run/decision/delivery evidence; see [27 Oct evidence update](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/55#issuecomment-6430763140) |
| #189 launch approval | **Closed as completed, 24 Oct; checked 30 Oct** | Production go-ahead reported by the tech lead in [the closure record](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/189#issuecomment-6376253508). The launch-status document still asks for INZBC's original written approval link |
| #303 written residual-risk acceptance | Waiting on INZBC | Verbal acceptance reported; written condition not yet met |
| #45 site forms | Receiver merged (#433) | Form types, routing, retention and privacy notice are client decisions |

## Status report lines (client-owned delays)

Both moved on 24 Oct ([launch status](../launch-status-2026-10-24.md)). Until then they were the
client's, and the weekly rows below record them that way:

- **#55 first production run (checked 30 Oct):** open. Authorisation and PAT were reported
  available on 24 Oct, but the latest issue handoff still names the safe transactional/idempotent
  batch-import path and original authority, real source outcomes, run ID, analyst/QA/CEO decisions
  and permitted delivery/closeout records as outstanding. No real production run is established by
  the synthetic walkthrough. See the [27 Oct update](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/55#issuecomment-6430763140).
- **#189 launch approval (checked 30 Oct):** closed as completed on 24 Oct, following the tech
  lead's recorded production go-ahead. INZBC's original written approval is still to be linked in
  the [launch-status document](../launch-status-2026-10-24.md). This report does not grant new
  approval or change production, distribution or signing controls.

## Evidence checklist

| Done | Week | Evidence | Obj |
|---|---|---|---|
| [x] | W2 | #62 to #65 merged (16 Oct) | 2.2 |
| [x] | W3 | Gate-safety baseline, 48/48, with control knockouts (24 Oct) | 2.2 |
| [x] | W3 | Replay and tamper baseline, 200 runs (24 Oct) | 2.2 |
| [x] | W3 | Literature review, 17 sources checked against their records (24 Oct) | 2.1 |
| [x] | W3 | Solution domain written (24 Oct) | 2.1 |
| [x] | W3 | #344 decision recorded on the issue (24 Oct) | 3.1 |
| [x] | W4 | Judge vs golden set, live run: 8/8, kappa 1.0 (24 Oct) | 2.2 |
| [ ] | W4 | Blind QA reviewer labels for the 8 golden cases, then judge vs human | 2.2 |
| [x] | W4 | Practice PDR worksheet drafted from the evidence ([bhanu-pdr-worksheet.md](bhanu-pdr-worksheet.md)); reflective answers still mine to write | PDR |
| [ ] | W5 | Practice PDR feedback written down | PDR |
| [x] | W6 | Signed human decisions and hash-chained audit log (brought forward, 24 Oct) | 2.2 |
| [ ] | W7 | Before vs after table for all three harnesses (gate safety and replay done 24 Oct; judge vs golden set done 24 Oct; judge vs human waits on reviewer labels) | 2.2 |
| [x] | W3 | Decision record for the W6 change, four options compared ([ADR-0010](../decisions/ADR-0010-signed-human-decisions.md)) | 1.1 |
| [ ] | W7 | Reflective report ([scaffold](bhanu-reflective-report.md)), evidence index (below) and final worksheet ready by Fri 20 Nov | PDR |
| [ ] | W8 | Final PDR attended, Moodle upload done, feedback logged | PDR |

## Plan change log

| Date | Change | Why |
|---|---|---|
| 2026-10-24 | W6 change set: signed human decisions and a hash-chained audit log | The replay baseline found a forged human decision is accepted (0/200 detected). This is the change with the most direct link to the research question |
| 2026-10-24 | W6 change brought forward from 9 Nov | It needed no client input and the harness was ready. W6 and W7 now cover the judge measurements if W4 slips |
| 2026-10-24 | Added a live-model adversary and replay through Postgres | Two threats to validity ("the scripted model always complies", "not the persistence layer") could be measured with no client input |
| 2026-10-24 | Judge vs human split into two measurements | The golden labels are the rubric author's synthetic test labels, not a QA reviewer's decisions. Agreement with an independent reviewer has to be measured separately |

## Decision record (1.1)

How to close the forged-decision gap: database privileges only, server-held HMAC signatures,
per-approver signatures, or an external ledger. Chose HMAC, and recorded per-approver signatures
as the next step if INZBC needs proof of authorship. See
[ADR-0010](../decisions/ADR-0010-signed-human-decisions.md).

## Cycle time (1.2)

Issues assigned to me and closed in the week, from GitHub. "Days open" runs from when the issue was
created, not from when work started, so it overstates time spent working: most of these were
opened in early August as the backlog.

| Week | Closed | Avg days open (completed only) | Not planned | Blocked on INZBC | Note |
|---|---|---|---|---|---|
| W2, 12 Oct | 13 | 73.5 (11 completed) | 2 (#46, #201) | #55, #189 | #62 to #65 closed 16 Oct when the four AI builds merged |
| W3, 19 Oct | 0 | n/a | 0 | #55, #189 | Work went out as PRs instead: #433 to #446 reviewed and merged, #447 to #451 and #456 merged |
| W4, 26 Oct (partial) | 0 (0 completed) | n/a (no completed issues) | 0 | #55: original authority and real-run evidence still to record; #189 closed | As of Fri 30 Oct 2026, 08:03:50 NZDT; no issue-closure events in the interval. PR activity is excluded |
| W5, 2 Nov | | | | | |
| W6, 9 Nov | | | | | |
| W7, 16 Nov | | | | | |


### W4 snapshot evidence, 30 Oct 2026

**Incomplete week.** Count only issue-closure events in
`2026-10-25T11:00:00Z <= event.created_at <= 2026-10-29T19:03:50Z`
(Mon 26 Oct 00:00 through Fri 30 Oct 08:03:50 NZDT). This is an as-of snapshot, not the final W4
total. W5–W7 are future weeks and remain blank.

**Method and result.** The [repository issue listing](https://api.github.com/repos/India-New-Zealand-Business-Council/inzbc/issues?state=all&since=2026-10-25T11%3A00%3A00Z&sort=updated&direction=desc&per_page=100&page=1)
returned 80 records on its only page; 72 pull requests were excluded. The eight actual issues
were #55, #127, #130, #189, #198, #199, #344 and #493. Their full
`/issues/{number}/events?per_page=100` histories each fit on one page. None contains a
`closed` event in the interval. Therefore no closure can qualify as assigned to
`bhanuGupta1` at closure: **0 completed, 0 not planned, 0 total**, with no completed-only
average to calculate. The assignee-filtered closed-issue search was also empty; the all-issue
event scan avoids relying only on today's assignee or closed state. This is an issue-closure
measure, not a claim of no work or no PR activity.

Historical closures seen in those histories are outside W4: #130 on 7 Aug,
#344 on 23 Oct at 10:27:18Z and #189 on 23 Oct at 22:47:17Z (24 Oct NZDT).
Sources: [#130 events](https://api.github.com/repos/India-New-Zealand-Business-Council/inzbc/issues/130/events),
[#344 events](https://api.github.com/repos/India-New-Zealand-Business-Council/inzbc/issues/344/events)
and [#189 events](https://api.github.com/repos/India-New-Zealand-Business-Council/inzbc/issues/189/events).
The existing W2/W3 rows are not recalculated by this W4 snapshot.

**Judge prerequisite check.** At the same review, the default branch still has no
`apps/sip/core/eval/human-qa-labels.csv` (contents API returned 404), and no open PR matched
that filename. The committed judge report still records 8 golden cases, kappa 1.0 and 17/17 score
bounds, with 0 human-labelled cases and null human agreement/kappa. No live run or write was
attempted. Eight actual independent reviewer answers, with reviewer and date, are required first;
availability of a fresh, unexposed model credential was not verified. Existing measured results
are unchanged.

## Peer review and mentoring log (3.2)

| Date | Who | What I did | Outcome | Evidence |
|---|---|---|---|---|
| 13 Oct | Roshan | Pushed a fix to #394: a product reached through a synonym could rank below the general exports entry. Made the eval gate compare every question, not only the totals | Roshan kept the fix and adopted a test rule for future ranking changes | #394, his feedback log entry of 13 Oct |
| 23 Oct | Roshan, Paras | Reviewed and merged #433 to #446, plus inzview #9 and #10. Fixed the findings left on each myself, including the CI failure on #433 | All merged with CI green | The PRs and their review comments |

## Conflict resolution record (3.2)

| Field | Entry |
|---|---|
| Issue | Process proposals opened as issues before they were agreed: a review rota (#320), daily GitHub check-ins (#405), and follow-on tracking issues (#406 to #415) |
| People involved | Roshan, Paras, me as tech lead |
| What I did | Answered every proposal in one place, [engineering-answers-2026-10-16.md](../engineering-answers-2026-10-16.md), instead of across a dozen threads. Kept the analysis that was useful (ADR-0008 kept as a comparison) and the deliverables that were real (#390, #392, #406). Declined the rota and the check-ins, and pointed to the existing CONTRIBUTING.md rule: new process issues need prior tech-lead authorisation |
| Outcome | The tickets were closed as history. Review and merging stay with the tech lead, on a weekly cadence. Roshan's plan change log of 16 Oct records the outcome |
| What I would do differently (draft) | Explain the approval boundary and rationale earlier, keep one decision record, and ask for actual feedback rather than assuming how the decision landed |

## Stakeholder and mentor feedback log

| Date | From | Feedback received | What I changed because of it | Evidence link |
|---|---|---|---|---|
| | | | | |

## Daily log

| Date | Done today (PRs, issues, reviews) | Blocked or waiting on | Tomorrow |
|---|---|---|---|
| Fri 23 Oct | Reviewed and merged #433 to #446 and inzview #9 and #10. Fixed the review findings left on each, including a CI failure on #433. Closed inzview #8 | INZBC: #55, #189, sector graphics for the FTA Centre | Measure the agent baseline |
| Sat 24 Oct | Recorded the #344 decision. Gate-safety, replay and tamper baselines measured. Literature review, solution domain and this plan written. Signed decisions and the sealed agent log built and re-measured. Coordinator agent runnable from the app as a rehearsal. Live judge vs golden set recorded in #456: 8/8, kappa 1.0, 17/17 score bounds | Independent QA reviewer labels for judge vs human; INZBC: #55, #189 | Obtain blind labels, then re-run the live judge |

## Weekly journal

### Week 3, 19 to 23 Oct (updated 24 Oct)

**Planned vs what happened (draft).** The plan placed baseline measurements and reading in W3.
The committed work also brought the W6 signed-decision change forward to 24 Oct and recorded a
live golden-set judge result. That moves implementation ahead of the original timeline, but the
independent human comparison and practice PDR remain incomplete.

**What helped or got in the way (draft).** Reproducible harnesses let me compare the unsigned and
signed designs without waiting for a production launch. The knockout runs make a perfect block
rate more informative because they show the suite fails when controls are removed. The eight-case
judge set is small and uses labels I wrote, so it cannot stand in for independent QA. #55 and
#189 remain dependent on INZBC.

**What I will change (draft).** I would separate issue closure from active work time, record
feedback on the day it is received and reserve time for independent validation. I will keep
launch approval, engineering completion and research confidence as separate claims.

## Evidence index

| Obj | Artefact | Link or file | Date |
|---|---|---|---|
| 1.1 | Decision record for the W6 change | [ADR-0010](../decisions/ADR-0010-signed-human-decisions.md) | 24 Oct |
| 1.2 | Cycle time, feedback log, weekly journal | this file | from 23 Oct |
| 2.1 | Literature review, 17 sources | [agent-safety-literature-review.md](../research/agent-safety-literature-review.md) | 24 Oct |
| 2.1 | Solution domain | [agent-safety-solution-domain.md](../research/agent-safety-solution-domain.md) | 24 Oct |
| 2.2 | Baseline and after measurements, harnesses, committed results | [agent-safety-baseline.md](../research/agent-safety-baseline.md), `apps/sip/core/eval/` | 24 Oct |
| 2.2 | AI builds #62 to #65, signed decisions #448, agent in the app #449 | merged PRs | 16 and 24 Oct |
| 3.1 | This plan, timeline, change log, daily log, status report lines | this file | from 23 Oct |
| 3.2 | Peer review log, conflict record | this file | 13 to 23 Oct |
| PDR | Practice worksheet | [bhanu-pdr-worksheet.md](bhanu-pdr-worksheet.md) | 24 Oct |
| PDR | Reflective report | [bhanu-reflective-report.md](bhanu-reflective-report.md) | due 20 Nov |
| Handoff | Remaining work, owner and prerequisites | [bhanu-studio6-handoff.md](bhanu-studio6-handoff.md) | 24 Oct |
