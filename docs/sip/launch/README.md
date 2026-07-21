# SIP Controlled Launch Pack (v0.9 Review Drafts)

Operating documents for the 27-31 July 2026 controlled internal launch. These close the
gap where SIP-184/185/186/187/188/189 were referenced but never authored. Drafted from the
approved **SIP-050 v1.1** prompt and the **SIP Intelligence Database v1.9** model.

**Status: v0.9 Review Draft.** Not controlled/approved. The CEO and reviewers must review and
approve before Day 1. Do not treat these as SIP-191-level approved artifacts.

## What this is (and is not)
- **Is:** a manual, human-driven operating pack so the 5-day launch can run on the existing
  DB workbook + the daily-agent, with every control gate enforced by checklist.
- **Is not:** the SIP web application (RBAC, audit DB, state machine). That is Phase 2+, built
  properly with a security review. It is **not** achievable safely by 27 July.

## Hard controls (enforced by not building the send path; no secrets exist)
- Automated distribution: **off**. Member/external/public/social publication: **off**.
- Every Daily Brief needs a separate CEO approval before manual send.
- Fail-closed: any Critical condition stops the run/distribution.

## Files
- `launch-config.md` — dates, roles, recipient, disabled controls.
- `SIP-184_daily_run_SOP_v0.9.md` — the daily 14-step run procedure.
- `SIP-185_source_register_v0.9.md` — mandatory/selective sources + fallback.
- `SIP-186_daily_brief_template_v0.9.md` — the report structure.
- `SIP-188_qa_checklist_v0.9.md` — independent QA gate.
- `daily-run-record_v0.9.md` — per-run authority, coverage, CEO decision, manual-send, audit.

## Open decisions (see spec)
- Where the app eventually runs (host), Claude vs OpenAI, and the missing SIP-030/040/060/100
  specs the DB references. None block the manual launch.
