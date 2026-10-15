# ADR-0008: Delivery process for Studio 6

**Status:** Not adopted. Comparison retained as analysis; existing workflow continues.
**Date:** 2026-10-13
**Decision owner and approver:** Technical lead (defined in CONTRIBUTING.md)
**Contributors to the comparison:** Roshan Aryal, Paras, Bhanu Gupta

**Governance clarification, 16 October 2026:** This is a proposed method comparison, not
authorization to change team roles, review ownership or recurring reporting obligations.
The tech lead rejected the review-rota and daily-check-in proposals (#320 and #405),
and did not authorize a new process rollout.
Existing contribution and meeting rules remain in effect. No score has been entered on
Bhanu's behalf. New process issues need his prior explicit authorization.

## Context

Studio 6 runs from 5 Oct to 4 Dec 2026. Three part-time engineers share one client, INZBC.
On 13 Oct the repository has 41 open issues: 20 on Bhanu, 15 on Paras, 4 on Roshan and 2
unassigned. Six of them are labelled `stage:blocked`, and several wait on a decision only the
client can make: the SIP-184 production run needs a fresh SIP-191 authority (#55), post-capstone
ownership and OAuth registration (#97), and signed client sign-off (#134). Review was also raised
as a historical bottleneck in #320. That snapshot listed seven PRs; by 16 October, six had
merged and news-agent #14 remained open. It is not a current count of unreviewed work.

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
| Risk | 2 / 5 / 1 | | 2 / 5 / 1 |
| Feasibility | 2 / 4 / 3 | | 2 / 5 / 2 |
| Scalability | 4 / 4 / 2 | | 4 / 4 / 2 |
| Fit with client gating | 2 / 4 / 4 | | 2 / 5 / 3 |

Roshan's reasoning, scored 13 Oct before seeing anyone else's:
- **Risk.** Kanban 5: a blocked item is relabelled and the next one pulled, which is exactly what
  #55 and #97 need. Scrum 2: a blocked client decision breaks the sprint commitment. Waterfall 1:
  one blocked phase stops everything behind it.
- **Feasibility.** Kanban 4: the stage labels already exist, so it is a rule change. Scrum 2:
  planning, review and retro take hours a part-time week cannot spare. Waterfall 3: little
  ceremony, but the plan would need rewriting every time INZBC answers a question.
- **Scalability.** Scrum and Kanban 4: both work for a bigger team or a new member. Waterfall 2:
  scope changes mean replanning the whole block.
- **Fit with client gating.** Waterfall wins a point back here. Its phase gates match INZBC's
  SOP-driven sign-off (SIP-184, SIP-191), so it scores 4 alongside Kanban. Scrum 2: client gates
  do not line up with sprint boundaries.

Roshan's weighted totals (score x weight / 5): Scrum 48, Kanban 86, Waterfall 48.

Paras's reasoning, scored 14 Oct against the matrix and context above, before reading Roshan's
reasoning text (the totals were visible from the merged plan's own review thread, the prose was
not):
- **Risk.** Agrees with Roshan's placement, independently — the two issues this directly bites on
  are mine: #198 and #199 share the one client blocker (Member Jungle, #192), confirmed while
  rewriting my own worklog for this block. Kanban relabels one and moves to the next without
  either stalling the other. Scrum 2, Waterfall 1.
- **Feasibility — scored one point higher on Kanban than Roshan's.** My own work this block is a
  lot of small, independently-mergeable UI PRs across several apps, not one big sequential build —
  that is close to the Kanban shape already, not just a label change. Scrum 2: same ceremony-cost
  objection as Roshan. Waterfall 2, not 3: a UI backlog this size (15 open issues) doesn't have the
  clean upfront sequencing Waterfall rewards, so I score it lower than Roshan did.
- **Scalability.** Same as Roshan — Scrum and Kanban both hold if the team or load changes,
  Waterfall doesn't.
- **Fit with client gating — scored differently from Roshan, and the gap is worth recording.**
  From the UI side, client gating reads as "wait on a business decision" (#192's cost question),
  not "wait on a SOP phase gate" the way SIP-184/SIP-191 reads from Roshan's side. Kanban 5: a
  blocked UI issue can sit labelled while everything else on my list keeps moving. Waterfall 3, not
  4: its phase-gate framing fits the SIP side's SOP sign-off better than it fits a client cost
  decision blocking two unrelated-looking issues at once. Scrum 2: unchanged reasoning.

Paras's weighted totals (score x weight / 5): Scrum 48, Kanban 96, Waterfall 38.

Sensitivity check on Roshan's scores: move 10 points from risk to scalability, and 10 from
feasibility to fit with client gating (weights 20 / 20 / 30 / 30). Totals become Scrum 52,
Kanban 84, Waterfall 52. Kanban still wins, by 32 points instead of 38, so the decision does not
hang on how heavily risk is weighted.

Same reweighting applied to Paras's scores: Scrum 52, Kanban 94, Waterfall 42. Kanban's margin
over the next closest (Scrum) narrows from 48 to 42 — the same direction Roshan's check found
(38 to 32) — so in both independent scorings the decision does not hang on how heavily risk is
weighted, even though the exact numbers differ scorer to scorer.

Two independent scorers in and Kanban leads by a wide, stable margin in both (86 and 96, next
closest 48 in both) — Bhanu's column is still open. Repeat the full averaged-scores comparison
once all three are in, per the process above; this is not yet the final number, only two of
three.

## Decision

On 16 October the technical lead declined adoption of a new delivery process for the current
project. Existing contribution rules, assigned implementation lanes, client approval gates and
the documented meeting cadence continue. The comparison and individual scores above are retained
as analysis; they do not authorize a rollout, a review rota, new reporting duties or reassignment.

The following were proposed working rules, not adopted policy:
- **Board columns:** `stage:next-up`, `stage:in-progress`, `stage:blocked`, then closed.
- **WIP limit:** one `stage:in-progress` item per person. A blocked item is relabelled
  `stage:blocked` and the next item is pulled.
- **Review ownership:** contributor PRs require the tech lead's approval; only the tech lead merges into `main`.
  The review rota proposed under #320 was not adopted. Peer feedback does not replace approval.
- **Cadence:** the existing meeting cadence in `docs/meetings/README.md` continues. The specific
  proposed retrospective dates and any additional reporting duties require tech-lead confirmation.
- **Milestone:** every issue the team plans to touch this block sits on the "Studio 6" milestone.

## How we will know it works

- Weekly cycle time (in-progress to closed) recorded every Friday in
  `docs/workstreams/roshan-studio6-plan.md`.
- PR time-to-first-review may be measured descriptively if approved; do not attribute changes
  to a review rota that was not adopted.
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
