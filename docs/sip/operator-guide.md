# SIP operator guide — running a daily intelligence run

User documentation for the people who run SIP: the analyst who produces the brief, the reviewer who
QAs it, and the CEO who decides on it. It walks through one full day in order.

This is the plain-language companion to the controlled documents. Where the two ever disagree, the
controlled document wins — `SIP-184` is the procedure of record, and this guide points at it
throughout.

**Before you start, know the two rules that override everything else:**
1. **Nothing is sent without a recorded CEO decision for that specific day's report.**
2. **If a control fails, the run stops.** A Critical failure is never downgraded to a warning, and
   never worked around to keep the day moving.

---

## Who does what

| Role | Person | Does |
|---|---|---|
| Analyst | Sunil (Bhanu is backup) | Opens the run, scans sources, captures and assesses candidates, drafts the brief |
| Quality Reviewer | Paras (Roshan is backup) | Independent QA against SIP-188. **Cannot be the same person who was the analyst for that run** |
| CEO / SIP Owner | Sunil | Records the daily decision and authorises distribution |

The analyst and reviewer for a run must be two different people. That separation is the point of the
QA step — it is not a formality, and the database enforces it.

---

## Before Day 1 (once only)

- [ ] Confirm launch authority is active and the date is inside the authorised window.
- [ ] Confirm you have the approved version set of the controlled documents.
- [ ] **Run the backup restore test.** Download a fresh copy of the Intelligence Database from the
      cloud, open it, and confirm every sheet loads. See `launch/backup-procedure_v0.9.md`.
      If the downloaded copy will not open, or the checksum does not match, **stop — do not start
      Day 1.**

---

## The daily run

### Step 1 — Open the run
Create a Run ID in the form `RUN-YYYYMMDD-01` and record it in the Production Run Register.

Confirm before going further: launch authority active, date inside the window, run type and operator
authorised, approved versions in use, no uncontrolled change since yesterday.

> **Stop here if** any of those is missing or unclear. No run authority means no run.

### Step 2 — Lock the coverage window
Exactly 24 hours, Pacific/Auckland time: **previous day 07:00 to current day 07:00**, start
included, end excluded.

Write the actual timestamps down. Never record a vague label like "today" or "overnight" — if the
window is not exact, the freshness test later has nothing to test against.

### Step 3 — Load the source worklist
Take the applicable mandatory sources from `SIP-185`, plus any triggered selective sources, plus the
current ACT-009 and WL-006 monitoring sources.

### Step 4 — Record an outcome for every mandatory source
This is the step most likely to fail QA, so take it slowly. **Every applicable mandatory source needs
an outcome. A blank is a Critical stop.**

Use only these six codes:

| Code | Use when |
|---|---|
| **Included** | Something from this source made it into the brief |
| **Context** | Useful background, but not counted as a new signal |
| **Suppressed** | Deliberately held back (duplicate, filler, repeated promotion) |
| **Inaccessible** | You could not reach it, after trying the fallbacks |
| **Excluded** | Checked and ruled out — record the reason (freshness, relevance or confidence) |
| **No Qualifying Item** | Reached it, read it, nothing today met the bar |

Two traps worth naming:
- **"No Material New Signal" is not one of these.** That is the *day-level* conclusion for the whole
  run (Step 9). A single source with nothing to report gets **No Qualifying Item**.
- **Duplicate, Not Applicable, Verification Failed and Outside Coverage Window** are extra notes you
  add *alongside* one of the six codes — never instead of one.

**If a source will not open** (Stuff and The Hindu BusinessLine are the known ones), work down the
fallback ladder rather than skipping it: direct access → search within the source → indexed site
search → recognised news index → RSS or approved feed → keyword search → secondary source for
discovery → verify the claim against an accessible official source.

Record every attempt. If it is still unreachable, mark it **Inaccessible** — that is an honest,
acceptable outcome. Silently leaving it blank is not.

> **Never** use an inaccessible article's headline as evidence for a High or Critical claim.

### Step 5 — Capture candidates
Capture everything potentially relevant *before* you start selecting. Each candidate needs its
source, publication and capture time, window status, headline, summary, URL, and an evidence link.

Capture first, judge second. Deciding while capturing is how relevant items get lost.

### Step 6 — Apply the relevance tests
Ask, in this order: does it affect New Zealand directly? Is there a real India–NZ angle? Does it
matter to INZBC or its members commercially, in policy terms, or operationally?

Exclude generic India news with no New Zealand consequence, however interesting it is.

### Step 7 — Score and verify
Score relevance, signal strength and source confidence using the approved framework.

**The verification rule:** a High or Critical claim needs official or high-confidence evidence.
Never build one on an inaccessible article, a snippet, an unverified social post, or a single weak
secondary source. If you cannot verify it, it does not go out at that signal level.

Signal strength is about consequence, not about how prestigious the source is.

### Step 8 — Carry forward what is still live
Only items that genuinely remain material. State the original event, what triggered it back into
view, what changed, and what is still open. Give it an owner and a review date.

A carry-forward is never presented as though it were new today.

### Step 9 — If there is nothing, say so
**A day with zero new signals is a valid, correct run.** Record the completed source coverage, any
carry-forwards, any exceptions, and conclude **No Material New Signal**.

Do not pad the brief to make it look busy. Filler is a quality failure, not a courtesy.

### Step 10 — Draft the brief
Use the `SIP-186` template. The first version of the day is always `v0.9 Review Draft`.

### Step 11 — Independent QA
The reviewer (not the analyst) works through `SIP-188`: source coverage complete, verification done,
relevance sound, brief accurate, database and tracker agreeing.

**Any Critical failure blocks release.** The run goes back for correction and re-review — it does not
proceed to the CEO with a known Critical open.

### Step 12 — CEO decision
The CEO records exactly one decision, with reason, conditions, owner, evidence and next review:

**Continue · Continue with Correction · Pause · Stop**

Then, as a **separate** decision: **Distribution authorised — Yes / No.**

Approving the report and authorising distribution are two different decisions. Approval alone is not
permission to send.

### Step 13 — Manual send (only if distribution was authorised)
Send the approved file manually to the authorised recipient. Record sent time, sender, channel,
recipient and delivery result.

There is no automatic send, by design. During the controlled launch, member, external, public and
social distribution are all off.

### Step 14 — Close out
Assemble the evidence pack, route records to the database, reconcile the tracker, record exceptions
and corrections, note the distribution result and set up tomorrow's carry-forwards.

If the tracker and the database disagree about anything, that is a **Critical stop** — reconcile it
before closing.

---

## When to stop the run

Stop, and record an exception, if any of these is true:

- No run authority, or the wrong/unapproved document version is in use
- The coverage window is missing or invalid
- A mandatory source has no recorded outcome
- A Critical claim is unverified
- The tracker and database contradict each other
- A human approval is missing, or distribution was not authorised
- Evidence retention failed, or there was a security or confidentiality incident
- The prompt, sources, scoring or workflow changed without control

A Critical failure is never downgraded to a warning to keep the day moving.

---

## Common questions

**Nothing happened today. Do I still do a run?**
Yes. Record the coverage and conclude No Material New Signal. That is a complete, correct run.

**A mandatory source is down. Can I skip it?**
No. Work the fallback ladder, record each attempt, and mark it Inaccessible if it stays unreachable.
Blank is the only unacceptable answer.

**I am both the analyst and the only person available to review.**
Then the run cannot pass QA today. The reviewer must be someone other than the run's analyst. Use
the backup reviewer.

**The CEO approved the report. Can I send it?**
Only if distribution was *also* authorised. They are two separate decisions.

**I found something big and important but cannot verify it.**
Capture it, record it as unverified, and do not present it as a High or Critical claim. Note it for
follow-up. Unverified material never carries a Critical claim.

---

## Where things live

| What | Where |
|---|---|
| The procedure of record | `launch/SIP-184_daily_run_SOP_v0.9.md` |
| Source register and fallbacks | `launch/SIP-185_source_register_v0.9.md` |
| Brief template | `launch/SIP-186_daily_brief_template_v0.9.md` |
| QA checklist | `launch/SIP-188_qa_checklist_v0.9.md` |
| Run record sheet | `launch/daily-run-record_v0.9.md` |
| Roles, dates, recipient, disabled controls | `launch/launch-config.md` |
| Backup and restore test | `launch/backup-procedure_v0.9.md` |
| The approved Master Prompt | `launch/SIP-050_master_prompt_v1.1.md` |
