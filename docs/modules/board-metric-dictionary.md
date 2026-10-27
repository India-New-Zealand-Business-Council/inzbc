# Board and executive dashboard metric dictionary (draft)

**Status:** specification only — not an approved dashboard, live data feed, or reporting baseline.  
**Tracks:** #195; module 9 in `docs/modules/dashboards.md`.  
**Decision authority:** INZBC metric owners; implementation must wait for approved systems of record, authorised read access, and data-quality checks.

## Calculation contract

All calculations must declare a reporting period `[start, end)` in **Pacific/Auckland**, an as-of timestamp, source system and extraction timestamp. Deduplicate by the source system's immutable entity ID, not name/email. Keep missing, unknown, zero and not applicable distinct; never silently replace missing data with zero. For a rate, show numerator, denominator and percentage; if denominator is zero, report **N/A**. Financial amounts must specify NZD, GST treatment and whether cash or accrual basis. Never sum personally identifiable records into a public dashboard.

## Proposed metrics (owner sign-off required)

| Metric | Working definition / calculation | Provisional source | Data owner / caveat |
|---|---|---|---|
| Total members | Distinct member records whose membership is active at period end | Member Jungle | Membership owner; define corporate vs individual counting |
| Paid members | Distinct members with a paid entitlement valid at period end | Member Jungle, reconciled finance record | Membership + Treasurer; exclude complimentary or pending |
| New members | Distinct membership starts effective within period | Member Jungle | Membership; do not count account creation |
| Renewals | Completed renewals in period / memberships due for renewal in period | Member Jungle | Membership; agree late/grace-period rules |
| Overdue accounts | Amount unpaid after approved due/grace date at as-of date; accompanying account count | Accounting system / Member Jungle | Treasurer; exclude disputed/void items per approved policy |
| NZ / India membership | Active organisations/members by approved country field at period end | Member Jungle | Membership; do not infer nationality from contact address |
| Membership income | Recognised membership revenue in period, after credits/refunds | Approved ledger | Treasurer; accounting basis to be signed |
| Sponsorship income | Recognised sponsorship revenue in period, after credits/refunds | Approved ledger | Treasurer |
| Event registrations | Distinct valid registrations for events occurring in period | Selected event platform | Events owner; distinguish registrations from attendees |
| Event attendance | Distinct checked-in participants / confirmed registrations for events held in period | Event platform | Events owner; report numerator and denominator |
| Event income | Recognised event revenue for events in period, net of reversals | Approved ledger | Treasurer; avoid duplicate ticket/payment exports |
| Website traffic | Sessions and unique visitors over reporting period | Approved site analytics | Website owner; consent settings and bot filtering required |
| Newsletter performance | Delivered emails, unique opens and unique clicks; delivery and click rates with explicit denominators | Approved email platform | Comms owner; opens can be privacy-distorted |
| Social reach | Platform-defined unique accounts reached, separately by platform | Official platform insights | Comms owner; no cross-platform unique-person sum |
| Trade enquiries | Distinct inbound enquiries created in period, with optional qualified subset | Approved internal CRM | Trade-services owner; define qualification before publishing |
| Business opportunities | Distinct verified opportunities created in period, segmented by stage | Approved opportunity register | Trade-services owner; avoid equating leads with realised outcomes |
| Government engagement | Distinct recorded formal meetings or submissions in period | Approved engagement register | CEO/delegate; disclose only aggregate authorised categories |
| SIP production | Controlled runs completed / scheduled runs due in period | SIP run/audit records | SIP owner; never count seeded demos as production |
| SIP quality | QA-passed runs / QA-assessed runs, plus corrections / released briefs | SIP audit and QA records | SIP owner; separate missing QA from failures |
| Outstanding actions | Open approved action-register items as of timestamp; show overdue count separately | SIP/action register | CEO/delegate; restricted detail, aggregate board view |
| Technology costs | Recognised hosting, licences, usage and support expense in period | Approved ledger and licence register | Treasurer/technical owner; distinguish allocated/shared costs |

## Dashboard release gates

1. **Source-of-record approval:** no dashboard integration may bypass the Member Jungle retain decision, the selected event platform, the ledger, or the SIP controlled audit trail.
2. **Permissions and confidentiality:** board summary uses approved aggregated access; restricted member, sponsor, introduction and SIP evidence remains in the authorised system.
3. **Reconciliation:** owner signs a sample reconciliation to source totals, date boundaries, duplicate IDs, cancellations, credits, and membership state transitions before each measure is labelled production-ready.
4. **Uncertainty:** missing feeds show `Unavailable — source not connected`, never a fabricated value. Display staleness, period, owner and calculation version.
5. **No write-back:** dashboards are read-only; no dashboard action may change approval, membership or payment records.
6. **Acceptance:** Finance/Membership/Events/Comms/SIP owners approve relevant rows; INZBC decides targets and reporting frequency separately. Track approvals in the decision register.

## Open decisions for INZBC

- Does “member” mean a paid organisation, a natural person, a portal user or an entitlement? Which count is board-authoritative?
- Which accounting system, ledger basis, GST convention and conversion policy govern revenue/cost reporting?
- Which event system is authoritative, and what counts as attendance or a cancellation?
- Who may see country, sponsor, trade-enquiry and SIP-level breakdowns, and what suppression threshold is needed for small groups?
- What reporting frequency, historical baseline, target and review owner apply to each KPI?

**Implementation note:** This document is deliberately a definition catalogue only. It creates no CRM, finance, event integration, new database or implied production permission. See `docs/modules/dashboards.md` and `docs/inzbc-ai-operating-system.md` §§6–7, 9.
