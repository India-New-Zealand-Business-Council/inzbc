# INZBC AIOS — Client Go-Live & Sign-Off Pack

**Prepared:** 20 November 2026 (Pacific/Auckland)  
**For:** Sunil Kaushal (INZBC Account / SIP Owner) & Executive Committee  
**Purpose:** Single-page decision and activation checklist covering the six external client/owner actions required to move the build-and-test-complete platform into authorised live production.

---

## Current Engineering Status (Verified 20 Nov 2026)

- **Main repository (`inzbc`):** CI run green — `1,694` Python tests passing (`95.36%` coverage), `481/481` frontend tests passing across all five UIs (`SIP`, `Comms`, `FTA`, `Dashboard`, `Member`), `ruff`, `eslint`, TypeScript, Storybook WCAG 2.2 AA, `gitleaks`, `Semgrep`, Docker build, and E2E passing.
- **News collector (`daily-india-nz-news-agent`):** `196` tests passing; staging source-freshness, RSS failure diagnostics, SQLite checkpoint recovery, and canonical SHA-256 export capture merged.
- **Public site (`inzview`):** Up to date, 0 open PRs.

> **Important:** Engineering completion does not authorise live deployment, cron activation, or external distribution. Each gate below requires an explicit owner action or written sign-off.

---

## Six Client/Owner Actions Required for Production Go-Live

| # | Tracking Issue | Owner | Action Required | Proof Needed to Close | Status |
|---|---|---|---|---|---|
| **1** | [`#99`](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/99) — Free-Tier Hosting | INZBC Account Owner + Tech Lead | Provision INZBC-owned Render Web Service + PostgreSQL using `render.yaml`, set production env secrets (`DATABASE_URL`, `SESSION_SECRET`, `DECISION_SIGNING_KEY`, GitHub OAuth credentials), and run `scripts/migrate.py up`. | Live service URL, `/health` 200 response, migration output, and owner confirmation. | `[ ]` Pending |
| **2** | [`#133`](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/133) — Client Acceptance Session | Sunil Kaushal + Tech Lead | Hold and record a live walkthrough of the deployed SIP, Comms, FTA, and Dashboard workflows against INZBC's acceptance checklist. | Dated session recording/notes and written client acceptance link. | `[ ]` Pending |
| **3** | [`#303`](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/303) — Comms Free-Prose Risk Acceptance | INZBC Security / Privacy Owner | Written residual-risk acceptance recorded (20 Nov 2026); staff follow the permitted-input policy in `docs/security/comms-release-gate.md`. | Written approval record linked on `#303`. | `[x]` Decided (file link on `#303`) |
| **4** | [`#509`](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/509) — Hourly Polling & Retention Approval | SIP Owner / CEO | Approved (20 Nov 2026): enable read-only public RSS/GDELT hourly polling with 14-day retention. Separate activation PR enables cron. | Signed decision fields on `#509` + separate activation PR. | `[x]` Decided (activation PR pending) |
| **5** | [`news-agent #11`](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/issues/11) — Apps Script Sheet Tab | `sunilkaushalnz@gmail.com` | In the Google Apps Script behind `GOOGLE_SCRIPT_URL`, replace the missing-tab early return with `var sheet = ss.getSheetByName(data.sheet) || ss.insertSheet(data.sheet);` and deploy a new version (or create a tab named `Production_Run_Register`). | Successful test write to `Production_Run_Register` without `Sheet not found`. | `[ ]` Pending |
| **6** | [`news-agent #17`](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/issues/17) — Publisher Usage Rights | SIP Source Owner | Confirm usage rights or approved fallback endpoints for blocked/failing feeds (e.g. Scoop, Indian Express, PIB, Beehive, MFAT, ORF) before claiming full source coverage. | Per-source rights decision recorded on `news-agent #17`. | `[ ]` Pending |

---

## Foundation Platform Decisions Recorded (20 Nov 2026)

- **Membership Platform & Portal (`#198` / F1):** **Keep Member Jungle** as the membership system of record; the INZBC Member Portal (`apps/member/ui`) remains a curated link-out hub to Member Jungle rather than duplicating membership storage.
- **Events & Delegations (`#199`):** **Standardise on Member Jungle** for events and registrations and retire overlapping Zoho Backstage functions.
- **Sector Opportunity Briefs (`#194`) & Sponsors/Trade Services (`#200`):** Implemented as backend modules and authenticated API endpoints (`/api/sector-briefs`, `/api/sponsors`, `/api/trade-services`) preserving all SIP verification, append-only evidence, and dual-consent confidentiality controls.

---

## Post-Go-Live Items (Unblocked Immediately After #99 & First Live Run)

- **`#39` (SIP-050 v0.2 Calibration):** Bounded batch scoring (`score_batch`) is already merged; once live candidates are captured, run prompt calibration against real articles.
- **Timed Backup & Restore Rehearsal:** Execute one timed restore of a real production PostgreSQL backup to an isolated database and record actual elapsed RTO.

---

## Sign-Off Record

- **INZBC Account / SIP Owner:** ___________________________ &nbsp; **Date:** ____ / ____ / 2026
- **Technical Lead:** Bhanu Gupta &nbsp; **Date:** ____ / ____ / 2026
