# Open questions for INZBC

For: Sunil Kaushal, Executive Sponsor. Compiled 21 August 2026 from the repository, not from
memory — every item below traces to a marker in a document, an open issue, or a control that
cannot be satisfied without an INZBC decision.

**Already settled — please do not re-answer.** All owner roles sit with you, with no deputy. The
redaction policy is approved and committed. Member Jungle is linked out rather than duplicated.
The brand palette is confirmed. The six decisions in
[client-decision-pack.md](./client-decision-pack.md) were settled on 13 August. Those are closed
and recorded; nothing here reopens them.

Items are grouped by what they block, not by topic. The first group is the short one that matters.

---

## 1. Four signatures. Nothing else in this list unblocks as much.

These are decisions only you can make. Each is a control that is built and tested but cannot be
called *in force* until it is signed, and each is currently the sole thing holding an issue open.

| # | What we need | Blocks | Why it needs you specifically |
|---|---|---|---|
| S1 | **Sign off the SIP adversarial security review.** [docs/security/sip-review.md](./security/sip-review.md) | [#40](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/40), and any staff use of the Comms Assistant | The review found and closed 18 defects. Its own acceptance criterion is a recorded sign-off before staff-facing use. We cannot sign our own review. |
| S2 | **Accept, in writing, the residual Comms Assistant exposure — or tell us to stop accepting free text.** | [#303](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/303), and therefore also #40 | Staff type a brief that is sent to an external model. We have shrunk what can be pasted, but no software can tell whether a person typed a member's name. This is a risk acceptance, not an engineering gap — see §1a below. |
| ~~S3~~ | ~~**Name a second person who can review and approve.**~~ **Answered 21 Aug 2026: Sunil holds every reviewer role for now, to be revisited later.** See §1b — this is a valid answer, and it changes how the control operates rather than satisfying it. | Separation of duties, [#189](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/189) | — |
| S4 | **Approve first deployment**, or tell us to keep it local. | [#99](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/99), [#97](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/97) | Nothing is deployed anywhere today. Distribution is off by default and stays off until you say otherwise. |

### 1a. The Comms Assistant question, stated plainly

The Comms Assistant sends a staff-written brief to an external AI model to produce a draft.

We built a filter that removes formatted identifiers — email addresses, phone numbers, tax and
company numbers. **It cannot remove a person's name, job title or employer written in ordinary
prose, and no filter can.** If someone types *"Priya Sharma, Chief Executive at Koru Exports,
opposed the offer"*, that sentence reaches the model exactly as typed.

We have reduced the risk: the old single free-text box is now four short, capped fields, and every
field carries a warning. That makes it harder to paste something wholesale. It does not make it
impossible to type a name.

So there are two honest options, and the choice is yours:

- **Accept it.** Staff are instructed not to enter personal or Board information, and we record
  that you have accepted the residual risk. Practical, and it is what most organisations do.
- **Close it.** We stop accepting free text entirely, which means the Comms Assistant only works
  from pre-approved material and becomes considerably less useful.

We are not recommending one. We are asking you to choose, because either way it should be a
recorded decision rather than a paragraph in an operator guide.

### 1b. One person holding every role — what that actually means

**Answer received 21 August 2026: all reviewer roles are Sunil, revisited later if needed.**

That is recorded and we are not asking again. It needs stating clearly, though, because it is the
answer the separation-of-duties control was written to detect rather than the one that satisfies it.

BR8 refuses to let the same person both do a thing and approve it — capture a candidate and verify
it, draft a report and pass its QA, author a comms draft and approve it. The check is against
*recorded acts*, not job titles, so holding several roles does not defeat it: the system still sees
one person on both sides and refuses.

With one named person, that refusal is the normal path rather than the exception. The system
already handles this and was built expecting it — `sod_exceptions` and `candidate_sod_exceptions`
let the act proceed **while recording that it happened, who authorised it and why**. It is not a
switch that turns the control off; it converts a refusal into a logged, attributable exception.

The consequence, stated so it is not a surprise later:

- Most runs will carry an exception record. That is the design working, not a fault.
- The audit trail will show one person on both sides of most decisions. Anyone auditing this
  afterwards — an assessor, an incoming administrator, a future board — will see that plainly.
- The control is real for the day a second person exists. Nothing needs rebuilding then; a second
  named user is the whole change.

If a second reviewer becomes available even part-time, the exceptions stop and the control starts
enforcing rather than recording. Worth revisiting before any production run handling member data.

---

## 2. Access and accounts we cannot obtain ourselves

| # | What we need | Blocks |
|---|---|---|
| A1 | **Register two GitHub OAuth applications at organisation level** (staging and UAT). Free. Step-by-step instructions available; happy to screen-share. | [#97](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/97), sign-in for every app |
| A2 | **Confirm multi-factor authentication is on** for the INZBC-owned accounts in [account-licence-register.md](./account-licence-register.md). A five-minute check nobody outside INZBC can perform. | Security register row 6 |
| A3 | **Read access to Member Jungle and Zoho Backstage**, enough to assess them. | [#192](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/192), and #201/#198 behind it |
| A4 | **Confirm who owns the deployed services and the OAuth app** after the capstone. Recorded default if unnamed: export, revoke, tear down. | ADR-0004 |

---

## 3. Costs and ownership we have deliberately left blank

[account-licence-register.md](./account-licence-register.md) records every account the platform
touches. Seven cost lines are marked `[[to confirm]]` because **we will not estimate a number and
let it read as a fact**:

Wix Vibe · inzbc.org domain · Member Jungle · Zoho Backstage · EmailOctopus · Render · NewsAPI

We need the annual or monthly cost and the paying entity for each. "Free" is a valid answer and we
will record it as one.

---

## 4. How long data should be kept

[system-of-record-and-retention.md](./data/system-of-record-and-retention.md) has six retention
periods marked `[[period]]`. These are legal and policy choices under the Privacy Act 2020, not
technical ones, so we have not guessed them:

| Data | Our suggestion, if it helps |
|---|---|
| Staff identity after someone leaves | Long enough that historic audit entries stay attributable |
| Audit records | Current financial year plus one, minimum |
| Candidate articles and source snapshots | 24 months |
| Trade enquiries and introductions | The shortest defensible period |
| Prospective member and contact data | Short, and consent recorded at collection |
| Backups | Follows the longest of the above |

We also need a **named owner** for six data categories in that document (member register,
membership applications, payments, sponsor contracts, events, legal documents). If the answer is
"Sunil" for all six, say so and we will record it.

---

## 5. Facts we cannot invent, needed before anything is published

These are marked `OPEN` in [client-answers.md](./client-answers.md). Repository rules forbid us
filling them with plausible-sounding content.

| # | What | Note |
|---|---|---|
| F1 | **Patron appointment date** | The public page names Bhav Dhillon but gives no date. The "Patron since 2023" claim is currently unsupported. |
| F2 | **Current constitution** or an approved governance summary | The public description is second-hand |
| F3 | **Exact membership fees** | Structure is known; figures must come from Member Jungle at publication time |
| F4 | **Sponsorship tier names, amounts, benefits, exclusivity** | From the final FY27 prospectus |
| F5 | **Current industry and government partner lists** | The public page shows unlabelled images. Showing a lapsed partner as current is a commercial problem |
| F6 | **Testimonials** — attributed, with written consent | We will publish none without both |
| F7 | **A member spotlight** — chosen member, written consent, confirmed story | Same |
| F8 | **Two figures to settle**: two-way trade — is it $3.68b or $3.95bn? And member count — 160+ or 200+? | Both appear in our drafts with different values. Neither goes into copy until confirmed |

---

## 6. Two smaller decisions

| # | Question |
|---|---|
| Q1 | **Where should the website end and the platform begin?** ADR-0007 proposes a boundary. It is written and waiting on your agreement. |
| Q2 | **If redaction strips so much from a brief that the remainder is useless, should the system send it anyway or refuse?** ADR-0006 §5. This is a judgement about acceptable output quality, not an engineering constant. Our suggestion: refuse. |

---

## What happens if we get no answer

Recorded plainly so nothing is silently assumed:

- **S1–S2 unanswered** → the Comms Assistant is not used by staff. It stays built and unusable.
- **S3 unanswered** → every run requires a recorded separation-of-duties exception. Legal, logged,
  and visibly weaker than the control intends.
- **S4 unanswered** → nothing is deployed. The system stays a local demonstration.
- **§3–§5 unanswered** → those documents ship with their `[[to confirm]]` markers intact. That is
  the honest outcome, and it is better than an invented number, but it is visible to anyone
  reading them.

Everything else in the build continues regardless of these answers.
