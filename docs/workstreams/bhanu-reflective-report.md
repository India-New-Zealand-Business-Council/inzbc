# Reflective report, Bhanu Gupta (Studio 6 scaffold)

**Due:** with the final evidence, Fri 20 Nov 2026.

**How this scaffold works.** The factual parts are filled in from the committed evidence, with
links. The reflection paragraphs are evidence-based drafts prepared at my request. I must personalise
and confirm them before assessment; they are not a record of unreported experiences or feedback.

## 1. What I set out to do

**Research question.** Can an AI agent run the daily intelligence process while hard-coded controls
guarantee it never skips a human approval step?

**What I built for it:**
- the coordinator agent and its audit replay (#62)
- semantic retrieval (#63)
- the advisory quality judge (#64)
- streaming Comms drafts (#65)
- signed human decisions (#448)
- the agent in the app, as a re-verified rehearsal (#449)

## 2. What the evidence says

- **The agent cannot cross a human gate.** 48 of 48 attacks were blocked, and removing each control
  lets its own attacks through. ([baseline](../research/agent-safety-baseline.md), section 1)
- **The audit log could be forged until the W6 change.** Detection went from 0/200 to 200/200, and
  safety tampering from 2396/2596 to 3196/3196. ([baseline](../research/agent-safety-baseline.md),
  section 5)
- **Judge vs golden set:** 8/8 verdicts agree, Cohen's kappa 1.0, with 17/17 score bounds met
  (#456; [baseline](../research/agent-safety-baseline.md), section 4).
- **Judge vs independent human QA:** Not measured. No independent reviewer's blind labels are
  recorded yet; the rubric author's golden labels and Codex review cannot substitute for them.

**Answer to the research question (draft).** The controls prevented all 48 attacks in the suite,
  and the knockout runs show that the suite can expose missing controls. That supports the design
  within the tested scenarios. It does not establish a general guarantee against every agent or
  attack. I wrote the scenarios, used a scripted adversary and replayed synthetic runs, so the next
  useful evidence would be independently designed attacks, persistence-layer checks and a larger
  set of realistic cases. The golden-set judge result is a regression check, not independent QA.

## 3. A decision I made, and how I would judge it now

Server-held HMAC signatures, not per-approver keys
([ADR-0010](../decisions/ADR-0010-signed-human-decisions.md)).

**Draft reflection.** I chose a change I could implement and measure within this block without
  introducing a client key-issuing process. HMAC closes the measured forgery gap for an attacker
  who can alter a log but does not hold the server key. The trade-off is that it does not prove
  individual authorship to a third party. I would reconsider per-approver signatures if INZBC
  needs that stronger claim and can support identity verification, key recovery and revocation.
  I would also treat historical verification during key rotation as part of the design rather
  than leaving it until the first rotation.

## 4. How I planned and managed the work

Facts:
- **Change log.** The W6 change was brought forward from 9 Nov to 24 Oct
  ([plan change log](bhanu-studio6-plan.md#plan-change-log)).
- **Cycle time.** 13 issues closed in W2. In W3 the work went out as PRs (cycle time table).
- **Client blockers.** #55 and #189 were blocked on INZBC throughout, and are recorded in every
  status report.

**Draft reflection.** The issue-closure table records 13 closures in W2, but it does not measure
  effort or show that batching saved time. W3 includes review, integration and research evidence
  that an issue count misses. I would record active start dates and separate engineering output
  from time spent waiting on decisions. Bringing the signed-decision change forward gave W6 and
  W7 room for measurement. While #55 and #189 remain client-dependent, I can continue independent
  research and verification without presenting that progress as production readiness.

## 5. Working with the team

Facts:
- **Peer review.** I reviewed and merged #433 to #446 and fixed their findings myself.
- **#394.** I pushed a fix to Roshan's #394, which he turned into a test rule.
- **Process proposals.** I answered the rota and check-in proposals in one record
  ([engineering-answers-2026-10-16.md](../engineering-answers-2026-10-16.md)).

**Draft reflection.** The record shows that I fixed findings while reviewing and integrating the
  work. It does not show whether doing so improved the other contributors' learning. I would
  distinguish urgent integration fixes from changes the author can own, and explain the reasoning
  behind a fix so the lesson is reusable. For process proposals, I would state the decision and
  its rationale in one place earlier. I cannot infer Roshan's reaction from a closed issue; that
  would need his actual feedback.

## 6. Feedback I received and what I changed

Practice PDR feedback is not recorded as at 24 Oct. After the meeting I will enter the actual
comment, my response and its evidence link in the plan's feedback log and worksheet section 6.
This section will then describe what changed; it cannot be completed from assumed feedback.

## 7. Using AI in this work

Facts:
- **Where AI helped.** I used AI assistance to draft code, documents and this scaffold.
- **How I checked it.** Every number is reproducible from a committed command and pinned in CI.
  Every literature source was checked against its publisher record (review, section 10).

**Draft reflection.** AI assistance produced code and document drafts, but the committed evidence
  is what supports the conclusions. A useful check in this work is separating agreement with
  labels written by the rubric author from agreement with an independent reviewer. Those are
  different claims even if their numerical results later match. I would ask a teammate to verify
  the source, reproduce the measurement and state its limits before accepting generated prose.
  I have not measured time saved, so I would not give an efficiency percentage.

## 8. What I would do next

**Draft next steps.** I would first obtain blind labels from an independent human QA reviewer
  and report both raw agreement and kappa, including any disagreement. I would then expand the
  attack set beyond my own scenarios and verify the deployed signing configuration in staging.
  Production enforcement depends on resolving legacy runs and retaining historical replay;
  it does not substitute for INZBC's launch approval. Per-approver keys would remain a separate
  decision, driven by whether INZBC needs externally verifiable individual authorship.
