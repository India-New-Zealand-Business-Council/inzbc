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

## Single source of truth
**This folder is the only home for the controlled SIP documents.** Do not copy these files into
another repository — a controlled document with two copies drifts, and the operator then follows
whichever copy they happened to open. (That is not hypothetical: the collection-engine repo
previously held a second copy, and its `SIP-185` fell behind the 22 Jul 2026 outcome-code
reconciliation.) The collection-engine repo links here instead.

## Files
- `SIP-050_master_prompt_v1.1.md` — the approved Master Prompt (controlling reference).
- `launch-config.md` — dates, roles, recipient, disabled controls.
- `SIP-184_daily_run_SOP_v0.9.md` — the daily 14-step run procedure.
- `SIP-185_source_register_v0.9.md` — mandatory/selective sources + fallback.
- `SIP-186_daily_brief_template_v0.9.md` — the report structure.
- `SIP-188_qa_checklist_v0.9.md` — independent QA gate.
- `daily-run-record_v0.9.md` — per-run authority, coverage, CEO decision, manual-send, audit.
- `backup-procedure_v0.9.md` — 3-2-1-1-0 backup and the pre-Day-1 restore test gate.

An operator-facing walkthrough of a full day, written for the people running it rather than for
engineers, is in [`docs/sip/operator-guide.md`](../operator-guide.md).

## Open decisions (see spec)
- Where the app eventually runs (host), Claude vs OpenAI, and the missing SIP-030/040/060/100
  specs the DB references. None block the manual launch.
