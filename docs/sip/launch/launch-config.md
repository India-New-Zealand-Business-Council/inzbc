# SIP Controlled Launch — Configuration (v0.9 Review Draft)

Authority: SIP-191 Production Launch Approval v1.0 (approved). Five-day controlled internal launch.

## Window
- Dates: 27 Jul 2026 to 31 Jul 2026 (inclusive).
- Daily run start: 07:00 NZ time (Pacific/Auckland).
- Coverage window: exact 24h, previous day 07:00 to current day 07:00, inclusive start / exclusive end.
- Day 5 review: 31 Jul 2026, 14:00-15:00 NZST. Launch expiry: 31 Jul 2026, 17:00 NZST.
- No continuation past 31 Jul without a separate controlled decision.

## Roles
| Role | Person |
|------|--------|
| CEO / SIP Owner | Sunil Kaushal |
| Primary Analyst | Sunil |
| Backup Analyst | Bhanu |
| Primary Quality Reviewer | Paras |
| Backup Quality Reviewer | Roshan |
| Secretariat distribution owner | Sunil |
| System Administrator | Sunil |
| Correction / withdrawal owner | Sunil |

- Analyst and Reviewer must be different people on any given run (separation of duties).
- System Administrator role carries no editorial or approval authority.
- Primary Quality Reviewer can independently stop a run.

## Distribution
- Authorised recipient: **Sunil Kaushal, sunilkaushalnz@gmail.com** (manual email only).
- Send only after the CEO records explicit distribution approval for that day's version.
- Never infer approval from silence or from a prior day's approval.

## Controls (must stay false; server-side once app exists)
```
automated_email_distribution   = false
member_distribution            = false
external_stakeholder_distribution = false
website_publication            = false
social_media_publication       = false
automatic_publication          = false
autonomous_run_approval        = false
autonomous_qa_approval         = false
SIP_PUBLICATION_ENABLED        = false
SIP_AUTOMATED_DISTRIBUTION_ENABLED = false
```
Changing any of these needs a controlled approval record.

## Approved version set (launch)
SIP-002 v6.9, SIP-050 v1.1, Intelligence Database v1.9, SIP-190 v1.0, SIP-190A v1.0, SIP-191 v1.0,
plus these v0.9 launch-pack drafts once reviewed. A version conflict is a High/Critical exception.

## Secrets
None supplied. No credentials in code, prompts, logs, reports, or repo files. Manual send uses
the operator's own approved email client, not an automated integration.
