# Usability study kit

**Prepared by:** Bhanu Gupta (tech lead), 24 Oct 2026. **Status:** ready to run; no sessions held yet.

The platform has strong evidence that it is *correct* and none yet that people can *use* it. This
kit is a short task-based study, sized for INZBC: 5 to 8 participants, 30 minutes each, run in
person or over video. Five participants find most of the serious problems in a single interface
(Nielsen and Landauer, 1993); a second round after fixes is worth more than a larger first one.

## Participants

| Group | Who | Modules |
|---|---|---|
| Staff | INZBC Secretariat, analysts, reviewers. Anyone who will use the platform | Trade Intelligence, Comms Assistant, assistant, Getting started |
| Members | 2 to 3 INZBC members who export to or import from India | FTA Explainer on inzbc.org |

Do not recruit anyone who built the platform. Record only a first name or a participant code.

## Before each session

1. Read the consent script below and record the answer.
2. Use a staging or demonstration environment with the seed dataset
   ([seed-demo-dataset.md](../seed-demo-dataset.md)), never a live run.
3. Clear the browser's site data so first-visit onboarding appears.

**Consent script.** "We are testing the software, not you. There are no wrong answers, and if
something is confusing that is what we want to find. I'll take notes and, with your permission,
record the screen. You can stop at any time. Is that okay?"

## Tasks

Read each task aloud. Do not explain the interface. Ask the participant to think aloud.

| # | Task | Success means | Module |
|---|---|---|---|
| 1 | "This is your first time here. Find out what you're allowed to do." | Reads Getting started and names one step for their role | Platform |
| 2 | "Find the run that is waiting for QA, and see who captured its candidates." | Opens Runs & Candidates, selects the run, finds the capture record | Trade Intelligence |
| 3 | "Ask the assistant which runs are waiting on QA." | Gets an answer naming the run | Assistant |
| 4 | "Ask the assistant to approve that run. What happens?" | Understands it cannot, and where approval is done | Assistant |
| 5 | "Draft a LinkedIn post about an upcoming event." | Produces a draft and can say who must approve it | Comms Assistant |
| 6 | "Find out what the FTA means for wool exports." | Finds the answer and its source | FTA Explainer |
| 7 | "Look up a product the FTA does not cover." | Understands there is no answer and what to do next | FTA Explainer |
| 8 | "Hide the introduction, then bring it back." | Uses "Got it", then "How this works" | Any module |

Members do tasks 6 and 7 only, on inzbc.org.

## Record per task

| Participant | Task | Completed (yes / with help / no) | Time (s) | Errors | What confused them (their words) |
|---|---|---|---|---|---|
| | | | | | |

## After the tasks: System Usability Scale

Ten statements, each rated 1 (strongly disagree) to 5 (strongly agree) (Brooke, 1996):

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

**Scoring.** For odd items subtract 1 from the rating; for even items subtract the rating from 5.
Sum and multiply by 2.5, giving 0 to 100. Report each participant's score and the mean; 68 is the
commonly cited average.

## Then ask

- "What was the hardest part?"
- "Was there anything you expected to be able to do and couldn't?"
- "Did anything make you doubt an answer?"

## Reporting

Report task completion rate, mean time and SUS per module, and list each problem with how many
participants hit it and its severity (blocks the task, slows it, cosmetic). For each problem,
record the change made and link its PR, then re-test the changed tasks in a second round. Never
estimate a number for a session that was not held.

## References

- Brooke, J. (1996). SUS: A "quick and dirty" usability scale. In *Usability Evaluation in
  Industry*, pp. 189–194. Taylor & Francis.
- Nielsen, J., and Landauer, T. K. (1993). A mathematical model of the finding of usability
  problems. *Proceedings of INTERCHI '93*, pp. 206–213.
