# SIP import issues: acceptance check, 19 November 2026

**Prepared by:** Roshan Aryal, for tech-lead review. **Scope:** issues #526, #528, #530, #531, #535,
#536 and #539, opened 3 November and implemented by PRs merged on 10 November. Each checklist item
was compared with the code and tests on the head of
[#561](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/561) (`main` plus restored
regression tests) and, for #535, [#564](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/564).

**Test run:** local PostgreSQL 14 with `database/schema.sql` applied to a fresh database (CI uses
16.2). On #561: `ruff` clean, `scripts/verify_restore.py` passed, `pytest apps services` 1680 passed,
4 skipped, coverage 95.30%. On #564: 1681 passed, 4 skipped. On current `main` the same run gives 6
ruff errors and 11 failed tests, which #561 fixes. None of this is a live SIP run, staging access or
production enablement; the importer is still unregistered and refuses runs without
`production_enabled`.

| Issue | Evidence for each checklist item | Gap | Ready to close |
|---|---|---|---|
| [#526](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/526) legacy capture lock | `candidate_persistence.py` takes `select production_enabled from runs ... for update` before insert and raises `BatchImportRequiredError` on production runs; API returns 409 (`test_production_legacy_capture_conflict_is_http_409`); Postgres tests `test_production_run_refuses_legacy_capture_before_candidate_or_audit`, `test_legacy_per_item_capture_cannot_race_atomic_import` | An unknown run returns **404**, not the 409 the issue named. Both are controlled responses, not a 500; tech lead to accept 404 or ask for 409 | After #561 merges |
| [#528](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/528) atomic import | `atomic_import.py` locks the run `for update`; tests for single commit and replay, two concurrent connections, missing authority, incomplete mandatory checks, stale run version, conflicting digest, rollback on second insert failure, unrecognised actor, run without production enablement; no route registers the importer | None found | After #561 merges |
| [#530](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/530) review packet | `apps/sip/collector/review_packet.py` with 8 offline tests (read-only packet, checksum binding, manifest tampering, plan mismatch, invalid run version, unreconciled source failures); `import_capture.py --apply` exits with "unavailable" | None found | Yes |
| [#531](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/531) bind text to checksum | Immutable original articles stored with the evidence (migration test `test_0009_...`); importer recomputes and compares headline and summary; tests for headline substitution, checksum mismatch, replay with same digest, payload limit | None found | After #561 merges |
| [#535](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/535) verify original text | Text and checksum checks as in #531. **Gap fixed in #564:** per-candidate audit stored the original headline; it now cites `evidence_ref#index`, with a regression test | Fixed by #564 | After #561 and #564 merge |
| [#536](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/536) staging preflight | `sip_staging_preflight.py` requires raw bytes from custody, 112 mandatory rows, DB source mapping; 11 tests (different custody, altered raw articles, replaced text, fake source UUID, ambiguous source name, missing register row, run version change, locked window, wrong run identity, naive time, valid packet not authorisation); output marks `source_rights_verified: False` | None found | Yes |
| [#539](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/539) full integration CI | Integration landed in `main` via #540 rather than a separate open branch; `test_collector_to_importer_full_synthetic_path` covers manifest to packet to preflight to import | Full CI is **not** green: `main`'s `sip-ui` build fails (type error in `apps/comms/ui/src/components/CommsAssistant.tsx`), so frontend and docker checks fail | No: after `main` builds and full CI passes |

Still outside engineering control for all of these: SIP-191 authority, source rights, the 112 human
source outcomes, an authenticated staging route and production activation (see
[handover status update](../operations/sunil-handover-update-2026-11-19.md)).
