# Studio 6 handoff, Bhanu Gupta

**Written:** 24 Oct 2026, after #447 to #451 merged.

What is done, and what is left, in the order to do it. A new session can start from this file:
everything it needs is in the repository.

## Done and on `main`

| PR | What |
|---|---|
| #447 | The research documents and baseline measurements: [plan](bhanu-studio6-plan.md), [literature review](../research/agent-safety-literature-review.md), [solution domain](../research/agent-safety-solution-domain.md), [baseline](../research/agent-safety-baseline.md) |
| #448 | Signed human decisions and a sealed agent audit log (the W6 change). Forged decisions detected went from 0/200 to 200/200 |
| #449 | The coordinator agent can be run from the app, on Run Detail, as a sealed rehearsal |
| #450 | A role-aware Getting Started walkthrough |
| #451 | Evidence documents: [ADR-0010](../decisions/ADR-0010-signed-human-decisions.md), [PDR worksheet](bhanu-pdr-worksheet.md), [reflective report scaffold](bhanu-reflective-report.md), and the evidence index |

## Left to do

### 1. Live judge run against the golden set (W4, needs a key)

**Who:** Bhanu adds the key; a session runs the measurement.

1. **Add the key.** In the environment settings (environment menu, then Edit), add
   `OPENAI_API_KEY` as a secret. Never paste a key into chat.
2. **Start a new session**, so the secret is loaded.
3. **Run the measurement:**
   ```
   uv run python -m apps.sip.core.eval.judge_agreement --live --write
   ```
   It writes `apps/sip/core/eval/results/judge-agreement.json`. The redaction policy comes from
   the eval fixture, which is fine because the 8 golden cases are synthetic. Production still
   needs the approved policy.
4. **Record the result:**
   - Fill the "Judge vs golden-set verdicts" row in the plan's baseline table.
   - Update section 4 of the baseline doc and section 2.2 of the PDR worksheet.
   - Tick the W4 checklist line.
   - Commit, open a PR with `Refs #64`, and merge it when CI is green.

**Done when:** the result file is committed and agreement is reported with Cohen's kappa.

### 2. Judge vs a human QA reviewer (W4 to W6, needs a person)

**Who:** a QA reviewer who did not write the rubric. Bhanu asks them in the team channel.

1. **Give the reviewer only the briefs.** Each case's brief text from
   `apps/sip/core/tests/data/quality-golden.json` goes to them on its own. Do not include the
   expected bounds or labels, or the labels are not blind.
2. **The 8 case IDs:**
   - `specific-supported-action`
   - `unsupported-tariff-claim`
   - `generic-india-news`
   - `vague-action`
   - `inflated-signal`
   - `instruction-injection`
   - `supported-watch-with-owner`
   - `duplicate-filler`
3. **The reviewer marks each case `needs_revision` true or false.** Save their answers as
   `apps/sip/core/eval/human-qa-labels.csv`:
   ```
   case_id,needs_revision,reviewer,date
   specific-supported-action,false,<name>,2026-10-30
   ```
4. **Re-run** step 1's command. The judge-vs-human row then fills in by itself.

**Done when:** the CSV is committed and the kappa is reported. Never estimate this number.

### 3. Practice PDR (W4 to W5)

**Who:** Bhanu.

1. Confirm the week with the facilitator and book the slot (2 to 6 Nov).
2. Finish the **[My own words]** parts of [bhanu-pdr-worksheet.md](bhanu-pdr-worksheet.md),
   sections 1.2, 3.2 and 5.
3. After the session, fill in section 6 of the worksheet and the feedback log in the plan, the
   same day.
4. Add a plan change-log entry for anything the feedback changes.

### 4. Reflection and journal (every week to 20 Nov)

**Who:** Bhanu only. These are assessed as his own words.

- The weekly journal in the plan, weeks 3 onwards.
- "What I would do differently" in the conflict record.
- Every **[My own words]** section of [bhanu-reflective-report.md](bhanu-reflective-report.md).
- The cycle-time rows for W4 to W7. The issue search used for W2 and W3 was assigned to
  `bhanuGupta1`, closed in the week.

### 5. Before vs after for all three harnesses (W7, by Fri 20 Nov)

Gate safety and replay are done (baseline doc, section 5). Add the judge rows once items 1 and 2
are in, then tick the W7 checklist line.

### 6. Final PDR (W8, 23 to 27 Nov)

- Rehearse.
- Upload to Moodle by **Fri 27 Nov, 10:30 AM**.
- Log the comments.
- Turn the worksheet into the final version.

### 7. Decisions only Bhanu or INZBC can make

| Decision | Owner | Note |
|---|---|---|
| Turn on `SIP_REQUIRE_SIGNED_DECISIONS` in production | Bhanu | Off for now. Turn it on once runs recorded before #448 are closed, or they stop replaying |
| Set `SIP_DECISION_SIGNING_KEY` in deployed environments | Bhanu | At least 32 bytes, held only by the server. Listed in the [secrets register](../secrets-register.md). Rotating it needs a re-verification plan |
| #55 first production run | INZBC | Needs a renewed SIP-191 authorisation and an approved PAT. Keep it in every status report |
| #189 launch approval | INZBC | Production launch approval is outstanding. Keep it in every status report |
| Per-approver signatures (ADR-0010, next step) | INZBC | Only if they need proof of authorship that does not rest on trusting the server |

### 8. Security housekeeping

Keys and passwords were pasted into a chat session on 24 Oct, and none of them were used.
- **Revoke all of them now.** Do the Google app password first: it gives access to the mailbox.
- **Re-issue only what is needed.** Put it in environment secrets, never in chat, a file or a
  commit.
