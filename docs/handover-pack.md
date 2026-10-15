# INZBC platform handover pack

Prepared 16 October 2026 for INZBC / Sunil, the confirmed post-placement owner (#97).
This assembles the existing material for #291. **The handover walkthrough has not happened**,
as corrected by the tech lead on 16 October. The pack is not evidence of that session.

## Operating material

- [Platform operator guide](operator-guide.md): sessions, roles and an end-to-end SIP day.
- [Controlled-launch operator guide](sip/operator-guide.md): workbook-based launch procedure.
- [Restore procedure](restore-procedure.md) and [backup design](backup-and-monitoring.md).
  CI verifies schema/append-only controls; a timed restore of an actual platform backup is still
  unproven. Closing #290 did not create that evidence. Do not claim a recovery time.
- [Secrets register](secrets-register.md): names and scopes only. INZBC / Sunil is accountable for
  the owned accounts and secret custody; transfer and runtime configuration need verification.
- [Security review](security/sip-review.md), [data-boundary ADR](decisions/ADR-0006-model-data-boundary.md),
  [model gateway configuration](model-gateway.md), and [incident response](incident-response.md).
- [Historical demo evidence](demo-evidence.md): local recording and screenshot locations/hashes;
  these artifacts must be included privately when delivering the pack, not assumed to be hosted here.

## Requirement to implementation to verification

This is a navigation matrix for delivered controls, not a claim that client UAT has passed.

| Objective | Implementation / contract | Verification / limitation |
|---|---|---|
| O1 governed SIP | `apps/sip/core/orchestrator.py`, `services/api/decisions.py`, `schemas/state-machine.md` | `apps/sip/core/tests/test_orchestrator.py`, `services/api/tests/test_decisions.py`; real-person UAT is separate |
| O2 sourced FTA answers | `apps/fta/explainer.py`, `apps/fta/corpus.py`, `services/api/main.py` | `apps/fta/tests/test_explainer.py`, `apps/fta/tests/test_eval.py`; API depth gap #392 remains |
| O3 controlled drafting | `apps/comms/draft.py`, `services/api/comms.py`, `services/api/model_gateway.py` | `apps/comms/tests/test_draft.py`, `services/api/tests/test_comms_api.py`, prompt/redaction tests; #303 written acceptance missing |
| O4 public website | [Website module](modules/website.md) | Cutover, redirect and accessibility evidence must be verified against the delivered site; this pack does not certify it |
| O5 shared controls | `services/api/session.py`, `services/api/auth.py`, `services/api/audit.py`, `database/schema.sql` | `services/api/tests/test_router_auth.py`, `services/api/tests/test_audit_coverage.py`; [data inventory](data/system-of-record-and-retention.md) retains its own approval status |
| O6 independent operation | Operator guide, secrets register and restore procedure above | Timed backup restore and recorded sponsor handover still required |
| O7 future scope | [Module specifications](modules/README.md), [current decisions](meetings/client/2026-10-16-decision-update.md) | Member Jungle retained; internal member/CRM builds not planned; Zoho deferred |

## Remaining decisions and delivery

| Item | Accountable owner | Consequence until complete |
|---|---|---|
| #189 production launch | Executive Sponsor | Testing/preparation only; production and distribution remain disabled |
| #303 written residual-risk acceptance | Executive Sponsor; tech lead records | Phone approval is reported, but the written condition remains unsatisfied |
| #133 live acceptance evidence | Tech lead / INZBC | Session and signed acceptance reported received for "everything"; original date, version-specific scope and record location still needed before marking detailed UAT criteria passed. #134 records receipt only |
| #45 forms routing/store/retention/notice | INZBC; tech lead finalizes contract | No internal receiver or additional personal-data store is authorized yet |
| #99 Render service | Tech lead / INZBC account owner | Account ready and preparation approved; no service exists or deployment verified |
| #291 sponsor walkthrough | Tech lead / Executive Sponsor | Pack ready for review; handover itself incomplete |
| #39 live calibration; #62–#65 engineering | Tech lead | These remain unfinished capabilities; documentation does not substitute for them |

## Walkthrough to complete with the recipient

Confirm account access privately, walk the operator through a real authorized SIP day, show a
refused action and the audit read-back, demonstrate recovery from an actual backup with recorded
timing, and record the session date, attendees, evidence location and remaining exclusions.
Use the [acceptance register](testing/acceptance-register.md) for actual observed results.
Do not copy credentials or confidential recordings into the public repository.
