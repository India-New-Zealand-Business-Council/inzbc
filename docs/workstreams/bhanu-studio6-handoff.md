# Studio 6 handoff, Bhanu Gupta

**Updated:** 24 Oct 2026 (Pacific/Auckland). Based on main after #456. This is a status and
operator handoff; it does not claim future meetings, personal reflections or production changes
have happened.

## Verified now

- #447 to #451 are recorded as delivered in the plan. #456 is merged: the live judge matched
  8/8 golden verdicts (Cohen's kappa 1.0) and 17/17 score bounds with `gpt-4.1-mini` and the
  approved redaction policy. Independent human agreement is still unmeasured.
- #455 is closed without merging. Its `docs/bhanu/studio6-handoff` branch is already absent
  (branch search and a direct ref read checked 24 Oct); no deletion was performed in this session.
- The baseline's before/after table now includes the golden-set judge row and a pending human
  row. W7 remains unticked until its remaining measurement is complete.

## Remaining work

| Item | Action and completion evidence | Owner | Due / prerequisite |
|---|---|---|---|
| Exposed credentials | Revoke the Google app password first, then other exposed credentials at their providers; re-issue only needed environment secrets. Record identifiers and outcomes, never values. See [secrets register](../secrets-register.md#exposure-response-24-oct-2026). No revocation is verified yet. | Account owner | Now |
| Independent human QA | Give only the [blind packet](../research/agent-safety-human-qa-packet.md) to a reviewer who did not write the rubric and has not seen expected labels or judge outputs. Import their actual answers as below, then run the live command. | Reviewer, then session | W4–W6 |
| Practice PDR | Book the course slot for 2–6 Nov. Personalise and confirm the evidence-based draft answers in worksheet objectives 1.2, 3.2 and section 5. After the meeting fill section 6 and the plan feedback log from actual comments. | Bhanu | 2–6 Nov |
| Reflection and cycle time | W3 journal, the conflict record and report reflection sections now have evidence-based drafts to personalise. Continue later weekly journals from actual experience. Populate W4–W7 cycle-time rows from actual GitHub events after each week; never fill future counts in advance. | Bhanu; session can calculate factual counts | Weekly to 20 Nov |
| W7 measurement table | Golden-set row is ready. After human QA, record raw agreement, case count and kappa, then check W7 only when all three harnesses' evidence is complete. | Session | Fri 20 Nov |
| Final PDR | Rehearse, attend the booked meeting, upload the final material to Moodle and verify the receipt. Record real comments and finalise the worksheet. No booking or upload is claimed. | Bhanu | Upload by Fri 27 Nov, 10:30 AM NZDT |
| Signing configuration | Follow [rollout and rotation prerequisites](../secrets-register.md#decision-signing-key-rollout-and-rotation-prerequisites). Set the server-only key before considering enforcement; deployed settings and legacy runs are not verified. | Tech lead / deployment operator | Before enforcement |
| Signing enforcement | Enable only after legacy runs are closed and staging checks succeed; maintain a path for unsigned historical replay. | Tech lead | Conditional |
| Per-approver keys | ADR-0010 next step only if INZBC needs it; no new key infrastructure commissioned. | INZBC | Conditional |

## Human labels: operator instructions (keep from the blind reviewer)

Provide only the packet file, not this mapping, the golden fixtures or the measured results.
The packet uses neutral IDs to avoid cueing verdicts with descriptive fixture IDs. Preserve the
reviewer's original answers. If the selected person has already seen the labels or results,
choose another reviewer rather than calling the exercise blind.

| Packet ID | CSV case_id |
|---|---|
| A | `vague-action` |
| B | `supported-watch-with-owner` |
| C | `unsupported-tariff-claim` |
| D | `duplicate-filler` |
| E | `specific-supported-action` |
| F | `instruction-injection` |
| G | `generic-india-news` |
| H | `inflated-signal` |

Create `apps/sip/core/eval/human-qa-labels.csv` only after receiving all eight real answers,
with exactly these columns:

```csv
case_id,needs_revision,reviewer,date
```

Use `true` or `false`, the actual reviewer name and their review date (YYYY-MM-DD). Validate
that all eight case IDs occur exactly once, with no extras or blanks. A template is not a result;
no placeholder CSV is committed at the loader's runtime path.

Then, in a configured environment using a fresh, unexposed model credential:

```bash
REDACTION_POLICY_PATH=config/redaction-policy.json uv run python -m apps.sip.core.eval.judge_agreement --live --write
```

Review `apps/sip/core/eval/results/judge-agreement.json`: status must be `measured`, and
`human_verdict_cases` must be 8. Report raw agreement and `human_verdict_kappa` (including
undefined if returned); do not assume agreement will be perfect. Update baseline section 4,
the before/after judge row, the plan and the worksheet with the measured result. Do not overwrite
recorded live evidence with a `--write` run that has no labels or lacks model configuration.

## Launch status

Both client dependencies cleared on 24 Oct, per the tech lead ([launch status](../launch-status-2026-10-24.md)):

- **#55 first production run:** unblocked. SIP-191 authorisation and the live-collection PAT are
  in place. Record the first production run once it has happened.
- **#189 launch approval:** cleared, and inzbc.org is live on the inzview build. Link INZBC's
  written approval and close the issue. The coordinator agent still cannot run production or
  distribute, by design.

Reflection and worksheet paragraphs have been drafted from the recorded evidence at Bhanu's
request. They need his personalisation and confirmation before assessment. Future journals,
actual feedback, independent human QA verdicts, meeting attendance and submission receipts
remain unrecorded until they happen. Codex review is model review, not independent human QA.
