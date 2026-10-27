# SIP-184 #55 — technical evidence handoff index (27 October 2026)

**Status: evidence checklist only; no production run has been verified.** Owner lane: Roshan
(collection and FTA). This index is **not** a run record, SOP, source register, permission,
CEO decision, approval, or a replacement for
[`daily-run-record_v0.9.md`](../../../docs/sip/launch/daily-run-record_v0.9.md).
Keep the actual approved controlled-document version and any client evidence in the
authorised system of record; link to it instead of copying it here.

## Entry conditions — all require actual evidence

| Gate / SIP-184 step | Evidence the responsible operator must retain | Evidence link / actual result |
|---|---|---|
| Launch, §1 | Current written SIP-191 authority, authorised dates/run type/operator and applicable controlled-document versions (the earlier July window expired); authority owner confirms permitted workflow | **Not supplied here** |
| Run identity, §1 | Platform-issued real `RUN-YYYYMMDD-NN`, actual run UUID/state and creation event; distinguish from `DRYRUN`/`WALK`/rehearsal | **Not recorded** |
| Coverage, §2 | Locked start/end timestamps, Pacific/Auckland offset, start inclusive/end exclusive, observed UTC duration and handling of any DST-day SOP conflict | **Not recorded** |
| Worklist, §3–4 | Approved SIP-185 v1.0 source register version and all applicable mandatory IDs (112 in the mirrored current register), selective sources and ACT-009/WL-006 additions | **Not reviewed against a real run** |
| Source outcomes, §4 | Each applicable mandatory stable `sip185_code` with exactly one of the six allowed outcomes, dated analyst confirmation, citation, and ordered fallback attempts; export from actual authenticated source checks | **No live 112-source result recorded** |
| Collection, §5 | Real collector execution time, environment, source fetch logs, source-health gaps, original capture path + SHA-256, and actual candidate counts; **fetch statuses are not SIP-185 outcomes** | **No live capture artifact attached** |
| Import, §5 | Authenticated, atomically locked/idempotent API batch import; server-side run-state/authority gate, digest key, audit inserts and two-writer replay/conflict test | **Blocked: API contract not implemented** |
| Reconcile, §5 | Capture digest linked to platform candidate IDs, UTC publication time, locked-window status, source-ID resolution, failed/rejected items and reconciliation of any gap | **Not done** |
| Assessment, §6–9 | Real candidate relevance, signal/verification decisions, High/Critical evidence, suppressions/duplicates and documented no-signal result if applicable | **Not done** |
| Brief and QA, §10–11 | Exact report/version, independent reviewer identity distinct from analyst, SIP-188 checks and treatment of Critical failures | **Not done** |
| CEO and distribution, §12–13 | Version-bound CEO decision and **separate** distribution authority; only if authorised, manual delivery evidence (retain recipient privately) | **Not done; never automatically send** |
| Close-out, §14 | State transitions, append-only decision/audit read-back, tracker/DB reconciliation, exceptions, evidence retention, backup and final run status | **Not done** |

## What existing code/PRs prove — and what they do not

- [News-agent #14](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/14):
  fetch-health reporting, timeout/recovery and distribution fail-closed **tests**, not a complete SIP-185 register.
- [News-agent #15](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/15):
  read-only, **rolling-window** capture export, not a locked-day production run.
- INZBC #472: offline manifest validator. INZBC #473: DST rule ambiguity tests.
  INZBC #474: authenticated **preflight only**; its `--apply` remains disabled.
- [INZBC #480](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/480):
  fixed a real producer/consumer `sectors` shape mismatch (merged 28 Oct); the manifest
  validator now accepts the upstream string form as well as the legacy list.
- [Launch status, 24 Oct](../../../docs/launch-status-2026-10-24.md):
  tech-lead report of cleared SIP-191 authority/PAT, **not** the primary signed record or a real run outcome.
- [Operator import guide](OPERATOR_IMPORT.md):
  current preview/stop conditions. Use it for technical preflight; do not bypass
  `apply_capture()` or call the older per-item `ingest_articles()` as a production
  substitute for atomic import.

## Handoff to responsible people

1. **SIP API owner / tech lead:** review transactionally locked and idempotent bulk-import
   endpoint and test two concurrent writers against one run. It must reject mismatched
   digest/replay and enforce exclusions against *all* other candidate-write routes.
2. **Authorised operator / client:** link the active written SIP-191 approval and
   approved document versions, then choose and document the specific live run window.
   Do **not** infer authority from a passing CI build or a 24 Oct summary alone.
3. **Analyst / QA reviewer / CEO:** complete the original controlled run record,
   source outcomes, candidate assessments, separation-of-duties checks and distinct
   decision and distribution records. Do not populate blanks with fixtures.
4. **Roshan's collector lane:** verify producer-to-consumer format and checksum on
   the actual operator-approved capture; hand the read-only report to the API owner.
   Do not touch a live API or record that a run passed until evidence exists.

**Closure gate:** Only close [issue #55](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/55)
once a real authorised `RUN-*` is linked to this evidence in the approved run
record and [launch status](../../../docs/launch-status-2026-10-24.md). Do not
commit private capture JSON, credentials, personal recipient details, or internal URLs.
