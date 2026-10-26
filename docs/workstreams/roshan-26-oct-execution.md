# Roshan lane — execution and evidence plan (26 October 2026)

**Scope:** Roshan's existing assigned work only, under `apps/fta/**`, `apps/sip/pipeline/**`, `apps/sip/collector/**`, service-side Comms, and the separate news-agent repository. This is an execution checklist, not a new client scope or an approval to operate. The [personal worklog](roshan.md) and [Studio 6 plan](roshan-studio6-plan.md) remain authoritative.

## Order of work

| Order | Work item | Work that can proceed | Completion evidence | External dependency / stop condition |
| --- | --- | --- | --- | --- |
| 1 | #387, literature review (due 30 Oct) | Examine all 12 annotation claims against source material actually accessed; check APA 7 and distinguish original full text, abstract, and publisher metadata; reconcile the #471 update | Citation-by-citation verification log, final revised literature review, reproducible references and PR review | Do not label metadata/abstract review as full-text checking or credit Bhanu's draft words as Roshan's own reflection without Roshan's review |
| 2 | #393, FTA lexical vs dense/hybrid | Inspect #469's offline harness and existing lexical baselines; lock provider/model, corpus snapshot, query/document representation and threshold-selection protocol; prepare test matrix for exact, multi-term, synonyms, product-framing and no-match | Immutable configuration and query IDs, matched per-variant result file, false-answer analysis by class, held-out score breakdown and reviewer sign-off | Do not invent embedding scores. Real gateway calls require approved access; threshold must be chosen on development data before held-out labels are consulted; production `answer_query()` remains unchanged |
| 3 | #55, SIP-184 live end-to-end | Reconcile collector PR #14/#15, read-only manifest validator #472, DST tests #473 and importer #474; collect run prerequisites; document operator steps and rollback/stop rules | Actual production run ID, UTC and NZ coverage interval, source register version, source outcome records, captured candidate counts, assessment results, operator authority and audit trail | Do not simulate live proof. #474's write mode stays disabled until API owner supplies atomic transaction/idempotency. Require named operator, SIP-191 permission, acceptable PAT and deployed API |
| 4 | Independent label checks following #406 | Prepare blinded adjudication sheet with query ID and independently supplied expected answer, without filling in any name or result | At least ten truly reviewed `checked_by` records plus dates and disputed-case resolutions | A protocol (#439) and closed issue (#406) are not evidence a person checked an answer |
| 5 | Studio 6 PDR and handover | Assemble existing PRs, research results, evaluation scripts, limits and decisions into the evidence index; complete draft worksheet and practice preparation | Dated links, exact test outputs, actual reviewer feedback, practice PDR record and final evidence by 20 Nov | Do not fabricate attendance, mentoring, feedback, emotions or personal reflection |

## Work already in review: avoid duplicate builds

- INZBC #469: **offline** dense/hybrid retrieval comparison. Review first; do not create a competing harness.
- INZBC #471: literature methodology/citation correction. Carry academic verification forward without replacing its claims of limited source access.
- INZBC #472: read-only collector manifest validation; #473: Auckland local-time and DST tests; #474: operator import preflight only. These are not evidence a production import ran.
- News-agent #14 and #15: freshness/recovery and review-only capture exporter. The latter is stacked on the former; neither may approve or distribute.

## Evidence contract for the next implementation PR

Every PR must state: linked issue; actual inputs and run mode (fixture, offline, staging or production); security/data boundary; reproducible command and resulting output; changed files; open risks; external approvals or human sign-offs still required; and the reviewer's highest-risk checks. Keep PRs open for Bhanu to review and merge. No direct push to main or edits to Bhanu/Paras-owned paths without consent.

## Immediate preparation checklist

- [ ] Verify original full-text availability for the 12 research entries; record abstract-only limitations honestly.
- [ ] Compare #469 against the issue #393 acceptance criteria without changing production ranking.
- [ ] Prepare a run record template for #55 with empty evidence fields until a real run exists.
- [ ] Seek independent question labels from a named human; do not write `checked_by` on their behalf.
- [ ] Confirm approval and atomic API write path with the owning people before live ingestion.
- [ ] Update the PDR worksheet and journal using only confirmed work and the student's own words.

**Scope exclusions:** #193 and #194 are not approved priorities; #38 and #64 belong to Bhanu; Paras owns the UI; the `inzview` website is paused at the client's request (26 Oct). No production execution, deployment, merge, client acceptance or sign-off is implied by this plan.
