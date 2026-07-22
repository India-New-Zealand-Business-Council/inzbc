# SIP-184 Daily Run SOP (v0.9 Review Draft)

The daily controlled-production procedure for each launch day. Runs on the Intelligence
Database v1.9 workbook + the daily-agent. Every step produces a record; skipping a step is a
QA failure.

## 1. Open the authorised run
Confirm: launch authority active (SIP-191), date within 27-31 Jul, run type authorised,
operator authorised, approved version set present, no uncontrolled change. Create Run ID
`RUN-YYYYMMDD-01`. Record in the DB Production Run Register.

## 2. Lock the coverage window
Exactly 24h, Pacific/Auckland, previous day 07:00 to current day 07:00, inclusive start /
exclusive end. Store actual timestamps. No vague labels ("today", "overnight").

## 3. Load the source worklist
From SIP-185: all applicable mandatory sources, triggered selective sources, ACT-009 and
WL-006 monitoring sources.

## 4. Record an outcome for every applicable mandatory source
Codes: Included, Context, Suppressed, Inaccessible, Excluded, No Qualifying Item (full detail
and sub-reasons in SIP-185). A blank mandatory-source outcome is a Critical stop at QA.

## 5. Capture candidate intelligence
Every potentially relevant item before selection, with full fields (candidate ID, source,
pub time, capture time, window status, headline, summary, URL, NZ/India/INZBC/member relevance,
signal, confidence, verification, duplicate status, decision, reason, routing). DB: Candidate
Intelligence + Raw Intelligence.

## 6. Apply relevance tests (SIP-050 §11-12)
Direct NZ relevance, India relevance, bilateral, INZBC strategic, member, commercial, policy,
operational, timing. Exclude generic India news with no NZ consequence.

## 7. Score and verify
Approved signal-strength + source-confidence framework. High/Critical claims require official
or high-confidence verification. Never build a High/Critical claim on an inaccessible article,
a snippet, an unverified social post, or a single weak secondary source.

## 8. Active Carry-Forward
Only unresolved items that remain material, with owner, review date and next watch point.
State original event, current trigger, what changed, what remains open. Not presented as new.

## 9. No Material New Signal
Zero new signals is a valid run. Record completed coverage, carry-forwards, exceptions, and the
No Material New Signal conclusion. No filler for volume.

## 10. Prepare the Daily Brief
Use SIP-186 template. First version is `v0.9 Review Draft`.

## 11. Independent QA (SIP-188)
Reviewer (Paras primary / Roshan backup) — must not be the run's analyst. Block release on any
Critical failure. Reconcile DB and tracker.

## 12. Present to CEO
CEO records one decision: Continue / Continue with Correction / Pause / Stop, with reason,
conditions, owner, evidence, next review, distribution authorised Yes/No, authorised version,
timestamp.

## 13. Manual distribution (only if CEO approved)
Send manually to sunilkaushalnz@gmail.com, approved file. Record sent time, sender, channel,
recipient, delivery result. No auto-send.

## 14. Close-out
Evidence pack, DB routing, tracker reconciliation, exceptions, corrections, distribution record,
final status, next-day carry-forward. Reconcile action IDs/owners/statuses/dates/routing/evidence
between SIP-187 and the DB. Any contradiction is a Critical stop.

## Fail-closed conditions (stop run or distribution)
No run authority; wrong/unapproved version; missing/invalid coverage window; mandatory source
without outcome; unverified Critical claim; tracker/DB contradiction; missing human approval;
unauthorised distribution; evidence-retention failure; security/confidentiality incident;
DB-integrity failure; uncontrolled prompt/source/scoring/workflow change. A Critical failure is
never downgraded to a warning.
