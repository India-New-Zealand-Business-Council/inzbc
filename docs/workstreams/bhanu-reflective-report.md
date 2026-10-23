# Reflective report, Bhanu Gupta (Studio 6 scaffold)

**Due:** with the final evidence, Fri 20 Nov 2026.

**How this scaffold works.** The factual parts are filled in from the committed evidence, with
links. Every **[My own words]** part is reflection: it is assessed as mine, so I write it. Delete
the prompts once answered.

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
- **Judge vs human:** [fill in once measured, or say plainly that it was not, and why]

**Answer to the research question:** [My own words. Prompts: How strong is "guarantee" given the
attacks were mine? What does the knockout table add? What would make me trust it more?]

## 3. A decision I made, and how I would judge it now

Server-held HMAC signatures, not per-approver keys
([ADR-0010](../decisions/ADR-0010-signed-human-decisions.md)).

[My own words. Prompts: Was speed the right reason? What would INZBC need for per-approver keys to
be worth it?]

## 4. How I planned and managed the work

Facts:
- **Change log.** The W6 change was brought forward from 9 Nov to 24 Oct
  ([plan change log](bhanu-studio6-plan.md#plan-change-log)).
- **Cycle time.** 13 issues closed in W2. In W3 the work went out as PRs (cycle time table).
- **Client blockers.** #55 and #189 were blocked on INZBC throughout, and are recorded in every
  status report.

[My own words. Prompts: What did batching the four AI builds into one day cost or save? How did
the client blockers change what I worked on?]

## 5. Working with the team

Facts:
- **Peer review.** I reviewed and merged #433 to #446 and fixed their findings myself.
- **#394.** I pushed a fix to Roshan's #394, which he turned into a test rule.
- **Process proposals.** I answered the rota and check-in proposals in one record
  ([engineering-answers-2026-10-16.md](../engineering-answers-2026-10-16.md)).

[My own words. Prompts: Was fixing other people's findings myself the right call for their
learning? How did declining the rota land with Roshan? What would I do differently?]

## 6. Feedback I received and what I changed

[From the feedback log, after the practice PDR: the feedback, what I changed, and the evidence.]

## 7. Using AI in this work

Facts:
- **Where AI helped.** I used AI assistance to draft code, documents and this scaffold.
- **How I checked it.** Every number is reproducible from a committed command and pinned in CI.
  Every literature source was checked against its publisher record (review, section 10).

[My own words. Prompts: Where did AI speed me up? Where did it get something wrong that I caught?
What rule would I give a teammate using it?]

## 8. What I would do next

[My own words. Candidates from the evidence:
- per-approver signatures (ADR-0010)
- a larger, systematic attack suite (baseline, threats to validity)
- a live judge run with a blind reviewer
- turning on `SIP_REQUIRE_SIGNED_DECISIONS` once legacy runs are closed]
