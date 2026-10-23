# Practice PDR worksheet, Bhanu Gupta

**For:** practice PDR, week 5 (2 to 6 Nov 2026). Keep this file and update it into the final
worksheet for week 8.

**How this was made.** Prepared with AI assistance from the committed evidence. Every number links
to a file that reproduces it. The sections marked **[My own words]** are reflection, and only I
can write them.

**The course's own worksheet.** If it has a different layout, copy these answers into it rather
than submitting this file.

## 1. My research question in one line

Can an AI agent run the daily intelligence process while hard-coded controls guarantee it never
skips a human approval step?

## 2. Evidence by objective

### 1.1 Making a decision between options

- **What I decided.** How to close the forged-decision gap the baseline found. There were four
  options, scored against measured results and against what fits this block:
  [ADR-0010](../decisions/ADR-0010-signed-human-decisions.md).
- **Why that option.** I chose server-held HMAC signatures over per-approver keys. Per-approver
  keys are the stronger option, but they need INZBC to issue keys and a browser signing flow. I
  recorded them as the next step.

### 1.2 Reflecting on my own practice and on feedback

- **Feedback received and what I changed:** [My own words, from the feedback log in the plan]
- **What the cycle-time data says about how I worked:** 13 of my issues closed in week 2, mostly
  in two days (15 and 16 Oct). In week 3 my work went out as PRs (#433 to #450) instead. [My own
  words: what that pattern says about batching, and what I would change]

### 2.1 Literature

- **The review.** 17 sources, each checked against its publisher record:
  [agent-safety-literature-review.md](../research/agent-safety-literature-review.md).
- **How it shaped the design:** [agent-safety-solution-domain.md](../research/agent-safety-solution-domain.md).
  - The model plans and code decides (Yao et al., 2022; Debenedetti et al., 2025).
  - Untrusted data is marked, but no guarantee rests on that (Hines et al., 2024).
  - Logs are bound cryptographically (Schneier & Kelsey, 1999).

### 2.2 Building and measuring

| Measurement | Before | After the W6 change |
|---|---|---|
| Gate-safety attacks blocked | 48/48 | 48/48 |
| Control knockouts that let their own attacks through (proves the suite can fail) | 4/4 | 4/4 |
| Runs replayed exactly | 200/200 | 200/200 |
| Forged human decision detected | 0/200 | 200/200 |
| Safety-relevant tampering detected | 2396/2596 | 3196/3196 |
| Metadata tampering detected | 0/1000 | 1000/1000 |
| Judge vs golden set | Not run yet | Needs `OPENAI_API_KEY` as an environment secret |
| Judge vs a human QA reviewer | Not measured | Needs blind labels from a reviewer |

- **Source of these numbers:** [agent-safety-baseline.md](../research/agent-safety-baseline.md),
  pinned in CI by `apps/sip/core/tests/test_research_eval.py`.
- **What the agent does in the app.** Staff can run it from Run Detail, and each trail is
  re-verified when it is read (#449).

### 3.1 Planning and managing my work

- **Plan and change log:** the plan with its dated change log, in
  [bhanu-studio6-plan.md](bhanu-studio6-plan.md).
- **Main change.** The W6 change was brought forward from 9 Nov to 24 Oct. That freed W6 and W7
  for the judge measurements.
- **Client-owned blockers.** These are kept in every status report so the delay stays recorded as
  INZBC's: #55 (SIP-191 authorisation and PAT) and #189 (launch approval).

### 3.2 Working with others

- **Peer review as tech lead.** I reviewed and merged #433 to #446 on 23 Oct, and fixed review
  findings and a CI failure myself rather than handing them back. I pushed a ranking fix to
  Roshan's #394, which he kept and turned into a test rule (his feedback log, 13 Oct).
- **Conflict.** #320 (review rota) and #405 (daily check-ins). I decided against both and recorded
  the answers in one place, [engineering-answers-2026-10-16.md](../engineering-answers-2026-10-16.md),
  rather than across several tickets. [My own words: how I handled it, and what I would do
  differently]

## 3. What I will show in five minutes

1. **The question, and why it matters for INZBC.** A daily brief that the agent can never
   publish or approve on its own.
2. **The attack suite.** One attack live: the model is told to skip QA, and the refusal is
   recorded. Then the knockout table, which shows each control matters.
3. **The gap the baseline found.** A forged decision, 0/200 detected.
4. **The change.** ADR-0010: why HMAC and not per-approver keys.
5. **After.** 200/200 detected, and the agent panel in the app showing a verified trail.

## 4. Questions I expect, and my answers

- **"Is 48/48 just because you wrote the attacks?"** Partly, and the baseline says so. The model
  is scripted to always comply, which is a stronger adversary than a real model. The knockouts
  show the suite can fail. AgentDojo-style suites are larger, and that is recorded under threats
  to validity.
- **"Why not per-approver signatures?"** ADR-0010: they are stronger, but they need the client to
  issue keys. They are recorded as the next step.
- **"Where is the human comparison for the judge?"** Not measured yet, and the baseline says so
  rather than estimating it. It needs a live model run and blind labels from a QA reviewer.

## 5. What I want feedback on at the practice PDR

[My own words]

## 6. Feedback received at the practice PDR

| From | Feedback | What I will change | Done |
|---|---|---|---|
| | | | |
