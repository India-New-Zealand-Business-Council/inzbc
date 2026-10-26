# Studio 6 plan, Roshan Aryal

Block 4 2026, 5 Oct to 4 Dec. Role: intelligence, sources, data and FTA. This file is the dated
copy of the personal plan and Gantt. Every log below is kept here so git dates each entry.

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
| W1, 5 Oct | Kick off and plan | Confirm PDR slots. Kickoff and triage. Commit this plan. Ask Bhanu about #63, ask INZBC about #55. Board Status access |
| W2, 12 Oct | Choose the process | Decision matrix and ADR-0008 draft. 48 hour review rota for #320. Collector PRs #13 and #14 (#208). Start literature search |
| W3, 19 Oct | Run it and read | Literature review annotations. Review #416 if Paras wants feedback. #344. (ADR-0008 not adopted, 16 Oct. Pairing arranged by conversation, not tracked as an issue) |
| W4, 26 Oct | Baseline and prep | Facilitate standup 27 Oct. FTA eval set and baseline. Annotated bibliography. Practice worksheet |
| W5, 2 Nov | Practice PDR | Practice PDR. Log feedback same day. Team sprint review on the existing cadence |
| W6, 9 Nov | Act on feedback | Revise plan, log the change. #393 comparison on approved work. Start evidence pack |
| W7, 16 Nov | Measure the change | Re-run eval, before vs after. Peer feedback by 18 Nov, asked in conversation. Evidence ready 20 Nov |
| W8, 23 Nov | Final PDR | Rehearse. Final PDR. Moodle upload. Log comments |
| W9, 30 Nov | Handover | Hand over open items. Close or reassign issues |

## Issues

Status checked against repository issues and main on **26 Oct 2026**. This is a
factual reconciliation of my existing plan, not a change in assignments,
review policy, ceremonies or client-authorisation rules.

| Issue | Status | Evidence / next step |
|---|---|---|
| #208 collection engine | Open; cross-repo PR #14 awaiting tech-lead review | Test source freshness, recovery and fail-closed behaviour; do not enable distribution |
| #55 SIP-184 production run | Open, **unblocked**, not executed | Tech lead's 24 Oct launch-status note records new SIP-191 authority and PAT. Requires an actual real collector-to-assessment run with run ID, outcomes, source evidence and approval trail; no claimed live success |
| #193, #194 | Not planned | Add only when INZBC explicitly prioritises |
| #63 embeddings | Closed, Bhanu's implementation | Shared gateway and semantic store delivered; #393's benchmark is still independent work |
| #344 Brief Builder source table | Closed | Tech lead selected manual, evidence-backed analyst outcomes, delivered through #446; real SIP-184 run remains #55 |
| #320 PR review backlog | Closed, not adopted | No review rota. Only tech lead reviews/merges |
| #384 FTA baseline | Done | #382 |
| #385 ADR-0008 process | Closed, not adopted | Retained only as analysis |
| #386 synonym gap | Done | #383 |
| #387 literature review | Open | 12 structured draft annotations (Bhanu's 23 Oct expansion), 12 bibliographic source checks; Roshan still to review and complete his own account by 30 Oct |
| #388 cross-run source health | Closed | Per-run only; durable counters deferred to live-run follow-up |
| #389 product ranking | Done | #394 |
| #390 held-out FTA questions | Closed | #416, ten synonym questions, including two duplicate texts |
| #391 eval regression gate | Done | #394 |
| #392 FTA depth API | Closed | Tech lead's #433 track, not mine to review |
| #393 compare rankers | Open | Four lexical variants already scored; PR #469 adds offline dense/hybrid evaluation, with real authorized scores and independent held-out labels still required |
| #404 steel exports | Done | INZBC approved general answer with missing-coverage warning |
| #405, #407–#415 process issues | Closed, not planned | Do not revive unauthorized ceremonies |
| #406 expected-answer review | **Closed 23 Oct; evidence incomplete** | The CSV still lacks checked_by labels despite documented blinded-review protocol (#439); cannot assert that ten checks occurred |

**Open, review-only work in my lane:** daily-india-nz-news-agent PR #14;
INZBC PR #469 (26 Oct, no production ranker changes). Neither may be merged
without Bhanu's review. The client's 26 Oct request pauses `inzview` work,
which is not in my implementation lane.

## FTA retrieval eval (2.2)

Eval history: the original baseline used 42 questions; the synonym-map comparison used 46.
The **current** `apps/fta/eval/questions.csv` has 55 questions (including product-framing
and no-match cases) as of 26 Oct; keep the archived baseline rows separate from present scores.
Harness:
`uv run python -m apps.fta.eval.run_eval --write <name>`. Baseline saved to
`apps/fta/eval/results/baseline.json`.

| Metric | Baseline | Synonym map | Framing terms (#389) | After #63 |
|---|---|---|---|---|
| hit@1 | 0.722 | 0.944 | 1.000 | |
| hit@3 | 0.778 | 1.000 | 1.000 | |
| MRR | 0.750 | 0.972 | 1.000 | |
| Multi-term hit@1 | 0.750 | 0.750 | 1.000 | |
| Synonym hit@1 | 0.200 | 1.000 | 1.000 | |
| No-match accuracy | 1.000 | 1.000 | 1.000 | |

Every metric is now at 1.000 on this set, so it can no longer tell a better ranker from a worse
one. The held-out questions (#390) are what #63 has to be measured on.

**Ranker comparison, 14 Oct (#393 groundwork).** BM25 scored the same as the live ranker on the
46 questions, but failed obvious cases like "dairy exports" and "salmon exports". The set had no
question pairing a product with a framing word, so six were added (now 52). On those:

| Variant | Product + framing hit@1 | Overall hit@1 | No-match |
|---|---|---|---|
| Keyword (live) | 1.000 | 1.000 | 1.000 |
| BM25 | 0.333 | 0.714 | 1.000 |
| BM25 + synonyms | 0.333 | 0.905 | 1.000 |

What it shows: plain BM25 lets a framing word that appears in only one topic ("exports") outweigh
the product, because rare terms get high IDF. The live ranker handles it only because of the
framing-term rule from #389 and Bhanu's fix in #394. Any embedding or hybrid change under #63 has
to beat that row, not the original baseline.

The synonym score is optimistic. The map was written with the ten synonym questions in view, so
it is partly fitted to them. A fair number needs ten new synonym questions written by someone who
has not seen the map. Asked Bhanu and Paras for these.

By type at baseline: exact 18/18 at rank 1, multi-term MRR 0.875, synonym hit@1 0.200 (2 of 10).
The keyword ranker has no way to match "lamb", "timber" or "international students" to the
entries that cover them. That gap is what the change in W5 to W7 has to close, without losing a
single exact or no-match result. Two multi-term misses (Q19, Q26) rank FTA-002 first because
"exports" matches its topic. To do: ask Bhanu or Paras to check 10 expected answers and fill the
`checked_by` column.

## Cycle time (1.2)

Every Friday: issues closed that week, days from in-progress to closed.

| Week | Closed | Avg cycle time (days) | Blocked items | Note |
|---|---|---|---|---|
| W2 | 0 | n/a | 4 team-wide (#39, #55, #97, #291). Mine: #55 | No issue closed yet. 3 PRs opened (#382, #383, news-agent #14 fixes), all waiting on review. Board and WIP limit not live until ADR-0008 merges, so W2 is the starting point, not a measured week |
| W3 | | | | |
| W4 | | | | |
| W5 | | | | |
| W6 | | | | |
| W7 | | | | |

## Plan change log (3.1)

| Date | Change | Why |
|---|---|---|
| 2026-10-13 | FTA eval set and baseline moved from W4 to W2 | Gives the literature review a measured problem to aim at, and frees W4 for the bibliography |
| 2026-10-13 | Synonym map started in W2, ahead of #63 | Literature review found the cheapest fix with no model call should be tried first. It also gives a middle row for the before vs after table |
| 2026-10-16 | ADR-0008 not adopted. No review rota, daily GitHub check-ins, retro issues or workload reassignment | Tech lead's answers of 15 to 16 Oct (engineering-answers-2026-10-16.md). Process ideas now go to the tech lead in conversation before any issue is opened |
| 2026-10-16 | #63, #64 and #38 stay with Bhanu. W5 to W7 retrieval work stays inside apps/fta (#393, #402) | No transfer approved |

## Stakeholder and mentor feedback log (1.2)

| Date | From | Feedback received | What I changed because of it | Evidence link | Obj |
|---|---|---|---|---|---|
| 2026-10-13 | Bhanu | Pushed a fix to #394: a product reached through a synonym ("salmon exports") could still rank below the overall exports entry, because synonyms score at half weight. Also made the eval gate compare every question's results, not only the totals | Kept the fix. Any future ranking change gets tested with framing words ("exports", "tariffs") plus a synonym product, not only a directly named one | #394, commit ab762da | 2.2 3.2 |

## Mentoring log (3.2)

| Date | Who | Topic and what I showed | Outcome | Evidence link |
|---|---|---|---|---|
| | | | | |

## Conflict resolution record (3.2)

| Field | Entry |
|---|---|
| Issue | #320: six PRs across both repos, mergeable and unreviewed. Work blocked |
| People involved | Bhanu, Paras, Roshan |
| Date raised | 2026-10-13, rota proposed on #320 |
| Steps I took | 13 Oct: proposed a 48 hour review rota on #320, rotating Bhanu, Paras, Roshan, reviewer named at Monday standup. Asked both to agree on the issue |
| Outcome | The tech lead closed #320 on 15 Oct as not planned: no rota is adopted, and review and merging stay with the tech lead. Context before the proposal: #381 waited 4 days for its first review, news-agent #14 waited 22 days (14 Aug to 5 Sep). PRs opened 13 and 14 Oct were reviewed the same day, but the rota was never adopted, so that is not evidence the rota worked |
| Evidence | #320 thread, the tech lead's answers in engineering-answers-2026-10-16.md, merged PR dates |
| What I would do differently | [My own words. Prompt: I proposed a process change and opened several tracking issues before agreeing them with the tech lead in conversation. What will I do next time I want to change how the team works?] |

## PDR evidence checklist

| Done | Week | Evidence | Obj |
|---|---|---|---|
| [ ] | W1 | Final PDR week confirmed, practice slot booked | PDR |
| [ ] | W1 | Kickoff notes with owners agreed | 3.1 |
| [ ] | W1 | Facilitator feedback on this plan logged | 1.2 |
| [x] | W1 | Board Status write access fixed (13 Oct, Status set on 13 items) | 3.1 |
| [x] | W1 | Studio 6 GitHub milestone created (13 Oct, 17 items) | 3.1 |
| [x] | W2 | Decision matrix and ADR-0008 draft (#382) | 1.1 |
| [ ] | W2 | #320 conflict record: issue, action, outcome | 3.2 |
| [x] | W3 | ADR-0008 outcome recorded: not adopted by the tech lead, 15 Oct, kept as analysis | 1.1 |
| [ ] | W3 | Notes from the team's existing sprint review and retrospective | 1.2 |
| [ ] | W4 | Annotated bibliography, 8 or more APA 7 sources | 2.1 |
| [x] | W4 | Baseline eval score committed (moved to W2, #382) | 2.2 |
| [ ] | W4 | Practice PDR worksheet | PDR |
| [ ] | W5 | Practice PDR feedback written down | PDR |
| [ ] | W6 | Feedback log: What I changed column filled | 1.2 |
| [ ] | W6 | Plan change log entry after practice PDR | 3.1 |
| [ ] | W7 | Before vs after table for #63 | 2.2 |
| [ ] | W7 | Honest review of what worked in my own process this block, from the journal and cycle time | 1.2 |
| [ ] | W7 | Peer feedback from Bhanu and Paras | 3.2 |
| [ ] | W7 | Reflective report, evidence index and final worksheet ready by Fri 20 Nov | PDR |
| [ ] | W8 | Final PDR attended, Moodle upload done, feedback logged | PDR |
| [ ] | Every week | Standup note, journal entry, mentoring log line | 3.1 3.2 1.2 |
| [ ] | Every fortnight | INZBC check-in feedback logged | 1.2 |

## Daily log

One line per working day, written before the 17:00 standup. It feeds the standup note and the
Friday journal, so the week never has to be rebuilt from memory.

| Date | Done today (PRs, issues, reviews) | Blocked or waiting on | Tomorrow |
|---|---|---|---|
| Tue 13 Oct | Opened #382, #383, #394. Fixed news-agent #14 review. Rota on #320. Reviewed and approved #381. Created #384 to #393. Created the Studio 6 milestone (17 items). Added #382 to #394 to the INZBC SIP Platform board and set Status, so board write access now works | Reviews from Bhanu and Paras. Bhanu's OK on #63, #64, #38, #392 | Client meeting. Chase reviews and ADR-0008 scores |
| Wed 14 Oct | Opened #398 and #399, both since merged. Reviewed Paras's ADR-0008 scores on #397. Bhanu approved #397 and it merged. Reopened #385 until the decision is written. Checked all 12 literature sources against the publisher record (review section 6). Dropped the Gao "main lever" sentence and the Carpineto drift claim, and removed an unverified Lewis page span. Wrote the Wednesday standup from the GitHub record. | Bhanu: news-agent #14 re-review, ADR-0008 column, answers on #392 and #63, #64, #38. Paras: #390 questions. PDR weeks are written in this file (practice 2 to 6 Nov, final 23 to 27 Nov) and are not confirmed with the facilitator. The practice slot is not booked. | Read the Carpineto and Romano article body, and the Robertson and Zaragoza body, before those claims go back in. Book the practice PDR once the facilitator confirms the week. |
| Thu 15 Oct | Opened #401 (ADR-0009 recommendation for #388), #403 (BM25 with the framing guard), #404 (steel exports question), #405 (daily standup thread) and #406 to #415 (standup actions). Paras opened #416 for #390: held-out synonym hit@1 0.800 with the map, 0.500 without | Bhanu: reviews of #400, #401, #403, news-agent #14 re-review, ADR-0008 column (due 16 Oct), #407. No replies yet on #405 from Bhanu or Paras | Review #416. Start annotations for #387. Confirm the PDR week and book the practice slot |

## Weekly journal (1.2)

One entry every Friday: what I planned and what happened, what helped or got in the way, feedback
received and what I will change.

### Week 2, 12 to 16 Oct (draft 13 Oct, finish Fri 16 Oct)

**Planned vs what happened.** Planned: decision matrix and ADR-0008 draft, review rota for #320,
get #13 and #14 merged, start the literature search. Done so far: ADR-0008 drafted and my column
scored (Kanban 86, Scrum 48, Waterfall 48), rota proposed on #320, literature review drafted with
11 sources. #13 was already merged. #14 had been waiting on three review points since 5 Sep, now
fixed and back with Bhanu. Not planned for this week but done: the FTA eval baseline (moved from
W4) and the synonym map (#383), which lifted synonym hit@1 from 0.200 to 1.000.

**What helped.** Measuring before changing anything. The baseline showed exactly where the
Explainer fails (synonyms), so the literature review had a real problem to answer and the
synonym map had a number to beat.

**What got in the way.** Review, again. #14 waited 22 days for its first review and #381 waited
4. Everything I opened this week is also waiting. The rota on #320 is the fix I am testing.

**Feedback received.** [Fill in Friday: anything from Bhanu, Paras, INZBC or the facilitator this
week, then copy it into the feedback log with what you changed.]

**How I felt about it.** [Your own words.]

**What I will change next week.** [Your own words. For example: commit standup notes the same
day instead of at the end of the week, or ask for reviewers by name when opening a PR.]

## Evidence index

| Obj | Artefact | Link or file | Date |
|---|---|---|---|
| 1.1 | ADR-0008 comparison (not adopted) and the tech lead's answers | [ADR-0008](../decisions/ADR-0008-delivery-process.md), [engineering answers](../engineering-answers-2026-10-16.md) | 2026-10-16 |
| 1.2 | Retro notes, cycle time table | this file | |
| 2.1 | Literature review | [retrieval-literature-review.md](../research/retrieval-literature-review.md) | 2026-10-13 (draft) |
| 2.2 | Eval set, baseline, PR | `apps/fta/eval/` | 2026-10-13 |
| 3.1 | Plan, Gantt, standups | this file, [W2 standups](../meetings/standups/2026-10-12-week.md) | 2026-10-13 |
| 3.2 | Mentoring log, conflict record, peer feedback | this file | |

## Reading list for 2.1 (verify each before citing)

- Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks.
  *NeurIPS 33*.
- Gao, Y., et al. (2023). Retrieval-augmented generation for large language models: A survey.
  arXiv:2312.10997.
- Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2023). RAGAS: Automated evaluation of
  retrieval augmented generation. arXiv:2309.15217.
- Robertson, S., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond.
  *Foundations and Trends in Information Retrieval, 3*(4).
- Karpukhin, V., et al. (2020). Dense passage retrieval for open-domain question answering.
  *EMNLP 2020*.
- Thakur, N., et al. (2021). BEIR: A heterogeneous benchmark for zero-shot evaluation of
  information retrieval models. *NeurIPS Datasets and Benchmarks*.
- W3C. (2013). PROV-DM: The PROV data model.
- NIST. (2023). Artificial intelligence risk management framework (AI RMF 1.0). NIST AI 100-1.
