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
| W3, 19 Oct | Run it and read | ADR-0008 merged 19 Oct, WIP limit live. Literature review. First pair session with Paras. Start #344. Retro 1 on 23 Oct |
| W4, 26 Oct | Baseline and prep | Facilitate standup 27 Oct. FTA eval set and baseline. Annotated bibliography. Practice worksheet |
| W5, 2 Nov | Practice PDR | Practice PDR. Log feedback same day. Start #63. Retro 2 on 6 Nov |
| W6, 9 Nov | Act on feedback | Revise plan, log the change. Build #63 against the FTA corpus. Start evidence pack |
| W7, 16 Nov | Measure the change | Facilitate standup 16 Nov. Re-run eval, before vs after. Retro 3. Team session on retrieval eval. Peer feedback by 18 Nov. Evidence ready 20 Nov |
| W8, 23 Nov | Final PDR | Rehearse. Final PDR. Moodle upload. Log comments |
| W9, 30 Nov | Handover | Hand over open items. Close or reassign issues |

## Issues

| Issue | Status | Note |
|---|---|---|
| #208 collection engine | Assigned | #13 merged 5 Sep. #14: Bhanu's three review points fixed and review re-requested 13 Oct |
| #55 SIP-184 production run | Blocked on INZBC | Needs a fresh SIP-191 authority. Tracked as a dependency |
| #193, #194 | Not planned | Only if the client raises priority |
| #63 embeddings | Proposed | Held by Bhanu. Ask first. Fallback: hybrid retrieval inside apps/fta |
| #344 Brief Builder source table | Proposed | Unassigned, in the sources lane |
| #320 PR review backlog | Proposed | Becomes the conflict record below |

## FTA retrieval eval (2.2)

Eval set: `apps/fta/eval/questions.csv`, 46 questions in four types (four no-match traps added
13 Oct with the synonym map). Harness:
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

## Stakeholder and mentor feedback log (1.2)

| Date | From | Feedback received | What I changed because of it | Evidence link | Obj |
|---|---|---|---|---|---|
| | | | | | |

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
| Outcome | PR time-to-first-review before and after the rota |
| Evidence | Standup note, issue comment, review rota, merged PR dates |
| What I would do differently | |

## Weekly journal (1.2)

One entry every Friday: what I planned and what happened, what helped or got in the way, feedback
received and what I will change.

## Evidence index

| Obj | Artefact | Link or file | Date |
|---|---|---|---|
| 1.1 | ADR-0008 | [ADR-0008](../decisions/ADR-0008-delivery-process.md) | |
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
