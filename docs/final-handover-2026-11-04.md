# Final handover, 4 November 2026

**Recorded by:** Bhanu Gupta, tech lead, 4 Nov 2026 (Pacific/Auckland).

This closes the placement's delivery and replaces the open acceptance rows in the
[handover pack](handover-pack.md). It records what the tech lead reported; INZBC's own written
record should be linked here when it is filed.

## Client acceptance

| Item | Status as of 4 Nov |
|---|---|
| Acceptance of delivered work (#133, #291) | Accepted. The tech lead reports that Sunil Kaushal, INZBC CEO and Executive Sponsor, has accepted everything delivered |
| #303 written residual-risk acceptance | Accepted, per the same report. Link the written record when INZBC files it |
| #189 production launch | Cleared 24 Oct ([launch status](launch-status-2026-10-24.md)), unchanged |

## Verification at handover

Run on `main` on 4 Nov 2026 with demo data only. No production data, credentials or model
provider were used, and none of this is a production run.

- Python suite: 1398 passed, 225 skipped (database-backed tests skip without Postgres); `ruff check`
  clean.
- FTA Explainer API started locally and queried over HTTP: `wool` returned a matched, cited answer
  (2.75% to 0%, MFAT National Interest Analysis p.13); `semiconductor export controls` returned
  `no_match` with the referral message and no invented answer.
- The FTA status line on every answer said the agreement was not yet in force. It entered into
  force on 20 October 2026; corrected in this change to match inzbc.org.
- Frontend tests run in CI on the pull request that adds this record.

## What INZBC receives

- The public website, inzbc.org, live on the `inzview` build. Changes go live only when someone
  publishes in Vibe.
- This repository: SIP pipeline and governance controls, FTA Explainer, Comms drafting with the
  redaction gate, dashboard, site-forms webhook receiver, and the documentation indexed in the
  [handover pack](handover-pack.md).

## Open after handover, owned by INZBC

Accepted as open. None of these is done, and nothing in this record should be read as saying so.

| Item | Where it stands |
|---|---|
| #99 hosting | No Render service exists. The platform UIs and API run locally only until one is created ([decisions needed](decisions-needed.md), section 3) |
| #55 first production SIP run | Not recorded. The import contract validates batches; the write endpoint stays disabled |
| #39 live scoring calibration | Measured on the golden set only. Needs real captured candidates |
| Backup restore | A timed restore of a real backup has not been done. Do not quote a recovery time |
| #60 Comms review UI | The approve endpoint exists; no reviewer screen was built (see `docs/workstreams/paras.md`) |
| #45 site forms | Receiver and tests exist; not connected to the live site's forms |
| `inzview` #13 | Preview pages for SIP, events and members, not merged |
