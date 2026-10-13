# ADR-0008: Delivery process for Studio 6

**Status:** Proposed. Draft for team scoring. Merge target 19 Oct 2026.
**Date:** 2026-10-13
**Deciders:** Roshan Aryal, Bhanu Gupta, Paras
**Decision owner:** Roshan (Studio 6 planning)

## Context

Studio 6 runs from 5 Oct to 4 Dec 2026. Three part-time engineers share one client, INZBC.
On 13 Oct the repository has 41 open issues: 20 on Bhanu, 15 on Paras, 4 on Roshan and 2
unassigned. Six of them are labelled `stage:blocked`, and several wait on a decision only the
client can make: the SIP-184 production run needs a fresh SIP-191 authority (#55), post-capstone
ownership and OAuth registration (#97), and signed client sign-off (#134). Review is the other
bottleneck: six mergeable PRs across both repos had no reviewer (#320).

So work arrives unevenly, a lot of it stalls on someone outside the team, and the block has a
fixed end date. The process has to keep work moving when one item is blocked, make review
happen, and still land the fixed-date deliverables.

ADR-0001 to ADR-0007 choose technology. None of them chooses how the team works. This ADR does.

## Options considered

Strengths and weaknesses are for this team and this block, not in general.

### Scrum (Schwaber & Sutherland, 2020)

Strengths
- Fixed sprints give natural checkpoints that line up with the practice and final PDR weeks.
- Sprint review and retrospective are built in, so reflection happens on a schedule.
- A sprint goal gives three part-time people one shared target.

Weaknesses
- A sprint commitment breaks when a client decision does not arrive. #55 and #97 have been
  blocked for weeks, and Scrum has no native way to show that.
- Planning, review and retro cost several hours per sprint, a large share of a part-time week.
- Velocity needs several sprints to stabilise. A nine-week block gives three or four at most.

### Kanban (Anderson, 2010)

Strengths
- Work is pulled one item at a time. When an item blocks, it is labelled and the next one is
  pulled, which matches how client gating actually hits this team.
- WIP limits expose the review bottleneck directly. A stalled PR holds a slot until someone
  reviews it.
- The board already exists: issues carry `stage:next-up`, `stage:in-progress` and
  `stage:blocked`, so adoption is a rule change, not a tool change.

Weaknesses
- No built-in timebox, so fixed dates (PDR weeks, 4 Dec handover) need a separate milestone.
- No built-in retrospective. The team has to schedule one.
- Without discipline the board drifts. In Studio 5 most items carried no stage label.

### Waterfall (Royce, 1970; PMI, 2021)

Strengths
- A full plan up front suits fixed-scope documents such as the handover pack (#291).
- Phase gates match the client's own SOP-driven sign-off style (SIP-184, SIP-191).
- Easy for the client to read: one plan, one set of dates.

Weaknesses
- The backlog changes weekly as INZBC answers questions, which invalidates an up-front plan.
- Testing and review come late, which is the opposite of what #320 needs.
- One blocked phase stops everything behind it.

## Decision matrix

Criteria and weights are agreed before scoring. Each person scores 1 (poor) to 5 (strong)
alone, then the scores are compared and averaged. Weighted score = average x weight / 5.

| Criterion | Weight | Scrum | Kanban | Waterfall |
|---|---|---|---|---|
| Risk (copes with blocked client decisions) | 30 | | | |
| Feasibility (fits three part-time people) | 30 | | | |
| Scalability (holds if load or team changes) | 20 | | | |
| Fit with client gating | 20 | | | |
| **Weighted total** | **100** | | | |

Individual scores, filled in before the comparison:

| Criterion | Roshan S / K / W | Bhanu S / K / W | Paras S / K / W |
|---|---|---|---|
| Risk | | | |
| Feasibility | | | |
| Scalability | | | |
| Fit with client gating | | | |

Sensitivity check: move 10 points from risk to scalability, and 10 from feasibility to fit with
client gating, then re-total. Record here whether the winner changes.

## Decision

To be confirmed once the matrix is scored. Expected outcome from the analysis above: Kanban, with
two borrowed Scrum practices (a fortnightly retrospective and a Studio 6 milestone with fixed
dates). If the scored matrix disagrees, the matrix wins and this section is rewritten.

Working rules if Kanban is chosen:
- **Board columns:** `stage:next-up`, `stage:in-progress`, `stage:blocked`, then closed.
- **WIP limit:** one `stage:in-progress` item per person. A blocked item is relabelled
  `stage:blocked` and the next item is pulled.
- **Review rota:** every PR gets a named reviewer within 48 hours of opening (proposed under #320).
- **Cadence:** standup note every Monday in `docs/meetings/standups/`, retros on 23 Oct, 6 Nov
  and 20 Nov.
- **Milestone:** every issue the team plans to touch this block sits on the "Studio 6" milestone.

## How we will know it works

- Weekly cycle time (in-progress to closed) recorded every Friday in
  `docs/workstreams/roshan-studio6-plan.md`.
- PR time-to-first-review before and after the rota, measured on #320's PRs.
- Count of `stage:blocked` items and how long each stays blocked.
- Each retro checks these numbers and changes one rule if the data says so.

## Consequences

- No sprint velocity. Forecasting uses cycle time instead.
- Fixed dates depend on the milestone, not the process, so the milestone must be kept current.
- Blocked client items stay visible on the board instead of being hidden inside a sprint.

## References

Ahmad, M. O., Markkula, J., & Oivo, M. (2013). Kanban in software development: A systematic
literature review. In *2013 39th Euromicro Conference on Software Engineering and Advanced
Applications* (pp. 9-16). IEEE. https://doi.org/10.1109/SEAA.2013.28

Anderson, D. J. (2010). *Kanban: Successful evolutionary change for your technology business*.
Blue Hole Press.

Project Management Institute. (2021). *A guide to the project management body of knowledge
(PMBOK guide)* (7th ed.).

Royce, W. W. (1970). Managing the development of large software systems. In *Proceedings of IEEE
WESCON* (pp. 1-9).

Schwaber, K., & Sutherland, J. (2020). *The Scrum guide*. https://scrumguides.org/

## Decision log

Objections raised in review and how each was answered go here, with the PR comment link.

| Date | Who | Objection | Response |
|---|---|---|---|
| | | | |
