# SIP-185 source-outcome integration — proposed decision for #344

**Status:** Design proposal for Technical Lead decision, not an approved implementation, change of ownership, or authority for live collection. The authoritative references remain SIP-184, the approved SIP-185 register, SIP-191 and the existing API/schema contracts.

## Actual state (23 October 2026)

The original issue describes the Brief Builder as wholly fixture-backed. That is no longer accurate. `apps/sip/ui/src/screens/BriefBuilderScreen.tsx` now requests `listCandidates(runId)`, `sourceLookup()`, and `listSourceChecks(runId)`. It maps recorded `source_id` UUIDs through `source_library` to SIP-185 codes and copies **only existing** check outcomes into the 112 mandatory-source rows. A missing check remains blank; the screen does not invent coverage. `apps/sip/ui/src/api/sourceLibraryClient.ts` supplies the source-library and per-run check GET calls.

The remaining question is **where real run-scoped outcomes originate and how they become accepted evidence**. `apps/sip/collector/source_register.py` defines the worklist and `record_source_outcome(...)` constructs a `SourceCheck`, but its caller must provide a justified `SourceOutcome`; the function does not visit the source or infer coverage. The separate news agent records source fetch health, which is **not automatically equivalent** to an SIP-185 coverage determination.

## Decision required from Technical Lead

| Option | Data path | Trade-off |
| --- | --- | --- |
| A: Analyst-confirmed manual outcomes | Existing run UI and API; analyst records each source's documented outcome from actual evidence | No undocumented inference; high 112-source workload |
| B: Proposed collection adapter + human confirmation | Authorized collection run emits source-id-linked evidence; adapter validates source identity and run window, proposes an outcome; analyst confirms using existing source-check write path | Reduces repetitive entry; requires a controlled semantic mapping, provenance and failure behavior |
| C: Automated final outcomes | Agent directly submits inferred SIP-185 outcomes without analyst confirmation | **Not proposed.** Fetch success or empty results cannot by itself establish `Included`, `No Qualifying Item` or `Excluded`; risks false coverage claims |

**Recommendation for review, not implementation authority:** evaluate B against the controlled launch rules; keep A until source mappings, client authorization and evidence semantics are approved. This document does not transfer UI or API ownership from Paras/Bhanu.

## Proposed evidence contract for B

A proposed check should preserve:
- Stable `sip185_code` and resolved `source_library.id`; never join on non-unique source names.
- Exact `run_id`, locked coverage window, collection attempt timestamp, source access URL/identifier, and acquisition method.
- Actual observed result: successful fetch with candidate references, successful fetch with *no qualifying result* after documented checks, access failure with attempts/errors, or a partial/inconclusive result. Distinguish `not attempted` from `attempted but inaccessible`.
- Full fallback trail per SIP-185, evidence references and source attribution. Candidate evidence must be associated with the same run and source.
- A human decision record where an observation is translated into the controlled SIP source-outcome enum; the actor, reason and audit event must be verifiable.

The existing enum (`Included`, `Context`, `Suppressed`, `Inaccessible`, `Excluded`, `No Qualifying Item`) does not encode arbitrary transient fetch states. **Do not coerce** a failed or partial fetch into `No Qualifying Item`. Leave an incomplete row without a final check until the approved fallback and human decision have happened.

## Fail-closed checks before a production integration

1. Reject unknown SIP-185 codes, ambiguous aliases, missing DB source ids, incorrect run ids and access to runs outside authorization. Preserve the current `SourceIdLookup` exact-type guard.
2. Never treat a quiet source, stale cache, partial GDELT query set, or unchecked source as proof of complete coverage. The current-run source-health fix in news-agent PR #14 remains a separate prerequisite.
3. Do not write `source_checks` from fixtures or a preview session. Use the existing authenticated persistence endpoint, its role policy and audit history; verify those independently in CI.
4. Do not overwrite analyst changes on a slow UI fetch or after switching runs; tests should exercise in-flight response ordering and user edits.
5. Gate QA on **all 112 mandatory source IDs** actually recorded with evidence. A blank or unresolved mandatory check stays a Critical stop. Optional sources must not be counted as substitutes.
6. Exercise an authorized end-to-end run (#55) only after INZBC renews SIP-191 authorization and supplies the approved PAT through secured secrets management. No live fetch is authorized by this proposal.

## Acceptance test cases to agree before implementation

| Case | Required result |
| --- | --- |
| Complete authorized run: source has qualifying candidate and cited source record | Proposed outcome can be reviewed; source id, run id, evidence and decision retained |
| Source attempted, no qualifying candidates, complete fallback procedure documented | Human may record `No Qualifying Item` only under approved rules |
| Timeout / HTTP error / partial query batch | Inconclusive, cannot be auto-certified as complete coverage |
| Source renamed or renamed across countries | Stable SIP-185 code resolves unique source; no name-based cross-link |
| Collector row from another run / old date window | Refused, never shown as current run's check |
| 111 of 112 mandatory sources checked | QA stays blocked; missing source shown by code |
| API unavailable / client GET fails | Existing fallback UI must not imply real persisted outcomes |

## Decision record requested (no new ticket)

Use existing issue #344 to record: (1) selected option; (2) authorized owner of the cross-repo adapter and API contract; (3) permissible source-health-to-outcome mapping; (4) audit/provenance requirements; (5) whether the initial rollout stays manual until #55. Do not implement an automated writer before this decision.
