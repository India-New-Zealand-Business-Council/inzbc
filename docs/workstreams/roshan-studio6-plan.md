# Studio 6 plan, Roshan (Block 4, 5 Oct to 4 Dec 2026)

Personal PDR pass-tracking, like the Studio 5 section in [roshan.md](./roshan.md). Not project
scope. Studio 6 is competency-based: all six objectives must pass.

Key dates from the Studio 6 PDR brief:

| What | When |
|---|---|
| Practice PDR | Week 5, 2 to 6 Nov |
| Evidence submission to Moodle | Fri 27 Nov 2026, 10:30 AM, no late submissions |
| Final PDR meeting | Week 8, 23 to 27 Nov (confirmed with the facilitator). All evidence ready by Fri 20 Nov |

## Gantt

```mermaid
gantt
    title Studio 6, Week 1 to Week 9
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    todayMarker on

    section 3.1 Plan and coordinate
    Kickoff, triage 41 issues, rebalance owners :a1, 2026-10-06, 4d
    Gantt and Studio 6 milestone                :a2, 2026-10-08, 2d
    Weekly standup notes (Mondays)              :a3, 2026-10-12, 50d
    Plan revision after practice PDR            :a4, 2026-11-09, 3d

    section 3.2 Support the team
    Review rota for the PR backlog (#320)       :b1, 2026-10-12, 5d
    Mentoring log, pair sessions with Paras     :b2, 2026-10-19, 33d
    Peer feedback forms                         :b3, 2026-11-16, 3d

    section 1.1 Choose a process
    Compare Kanban, Scrum, Waterfall            :c1, 2026-10-08, 8d
    ADR-0008 delivery process                   :c2, 2026-10-14, 5d
    Process agreed                              :milestone, 2026-10-19, 0d

    section 1.2 Apply and reflect
    Run Kanban with WIP limits, cycle time      :d1, 2026-10-19, 33d
    Retro 1                                     :milestone, 2026-10-23, 0d
    Retro 2                                     :milestone, 2026-11-06, 0d
    Retro 3                                     :milestone, 2026-11-20, 0d
    Weekly reflective journal                   :d2, 2026-10-09, 43d

    section 2.1 Specialist research
    Literature review, retrieval and provenance :e1, 2026-10-12, 19d
    Annotated bibliography (APA7)               :e2, 2026-10-27, 8d

    section 2.2 Integrate
    Land collector PRs #13 and #14 (#208)       :f1, 2026-10-12, 5d
    FTA retrieval eval set and baseline         :f2, 2026-10-27, 8d
    Embeddings for retrieval and dedupe (#63)   :f3, 2026-11-04, 13d
    Re-measure, before vs after                 :f4, 2026-11-16, 4d
    Production run, needs INZBC (#55)           :crit, f5, 2026-10-12, 40d

    section PDR
    Confirm PDR week, book slots                :g1, 2026-10-08, 2d
    Practice worksheet and evidence             :g2, 2026-10-27, 7d
    Practice PDR                                :g3, 2026-11-02, 5d
    Evidence pack and reflective report         :g4, 2026-11-09, 12d
    Evidence ready                              :milestone, 2026-11-20, 0d
    Final PDR meeting (Week 8)                  :g5, 2026-11-23, 5d
    Submit to Moodle                            :milestone, 2026-11-27, 0d
```

## Done so far (Studio 5, 22 Jul to 10 Sep)

24 issues closed: #52, #56, #54, #117, #118, #120, #121, #122, #130, #53, #31, #185, #186, #187,
#188, #209, #210, #218, #219, #271, #331, #332, #337, #338. Plus PR #359 (run authorisation and
the full Draft to Closed walk, refs #55) and daily-india-nz-news-agent #13 and #14 (#208).
v1.0.0 and v1.1.0 released 10 Sep. No commits yet in Studio 6.

Open on me: #55 (blocked on a fresh SIP-191 authority), #208, #193 and #194 (only if the client
raises priority).

## Evidence map

| Obj | Have | Will produce |
|---|---|---|
| 1.1 | ADR-0001 to ADR-0007 (technology choices, not process) | ADR-0008 delivery process: Kanban vs Scrum vs Waterfall decision matrix, APA7 references |
| 1.2 | Issue stage labels, PR evidence blocks, worklog | Three retros, weekly cycle time from GitHub, reflective journal, outcome vs goal table |
| 2.1 | MFAT source verification, #337 provenance report | Literature review and annotated bibliography on semantic retrieval, RAG grounding, provenance |
| 2.2 | #54 ranked retrieval, #208 freshness | FTA retrieval eval set, baseline in W4, #63 embeddings, re-measured in W7 |
| 3.1 | Issue assignments, Studio 5 worklog, one standup note | This Gantt, Studio 6 milestone, weekly standup notes, plan change log |
| 3.2 | Took six backend issues to balance Bhanu's load, #327 review rounds | Mentoring log, #320 conflict record, peer feedback forms |

## Proposed changes needing team agreement

- Take #63 from Bhanu (he holds 20 of 41 open issues). Fallback if he declines: a hybrid
  retrieval change inside `apps/fta` only.
- Pick up #344 and #320, both unassigned.

## Plan change log

| Date | Change | Why |
|---|---|---|
| 8 Oct | Plan created | Studio 6 Week 1 |
| 9 Oct | Final PDR confirmed for Week 8. Evidence deadline moved to Fri 20 Nov, peer feedback to W7 | Facilitator confirmed the dates |
| 9 Oct | Added feedback, mentoring and conflict logs, PDR worksheets | Criteria ask for stakeholder feedback integrated into planning, and peer-recognised mentoring |

## Stakeholder and mentor feedback log (1.2)

Log feedback the day it arrives. The last column shows feedback feeding into the plan.

| Date | From | Feedback | What I changed | Evidence | Obj |
|---|---|---|---|---|---|
| | | | | | |

## Mentoring log (3.2)

Ask the person helped to confirm each entry in a reply or comment.

| Date | Who | Topic and what I showed | Outcome | Evidence |
|---|---|---|---|---|
| | | | | |

## Conflict resolution record (3.2)

| Field | Entry |
|---|---|
| Issue | #320: six PRs mergeable and unreviewed |
| People involved | |
| Date raised | |
| Steps I took | |
| Outcome | |
| Evidence | |
| What I would do differently | |
