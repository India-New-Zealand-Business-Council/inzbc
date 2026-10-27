# SIP client walkthrough — 27 October 2026 (review draft)

**Audience:** Sunil / INZBC, Bhanu, Paras, Roshan. **Purpose:** show what SIP actually does and collect feedback **before** changing scope or claiming a production launch.

> **Status boundary:** This is a briefing aid, not an approval, a production run, evidence of real source coverage, or permission to send a report. The 24 October [launch status](../launch-status-2026-10-24.md) relays production authorisation and availability of collection credentials, but the source authority and actual run are not attached. The current staff platform is not confirmed deployed. See [#55](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/55).

## The simplest explanation for INZBC

SIP is **a staff-controlled daily intelligence workflow**, not a chatbot that sends arbitrary news. It aims to collect New Zealand–India trade developments, check source coverage, assess relevance and verification, draft a structured Daily Intelligence Brief, and require human QA plus an explicit CEO decision **before any authorised manual distribution**. Automation can assist; it cannot grant itself approval.

A separate public website is already live, but it is **not** the SIP platform; a working public site is not proof that a real SIP run has completed.

## What exists, what has been exercised, and what is still missing

| Step | Implemented / demonstrated | Not yet established in production |
|---|---|---|
| Discover / collect | News agent and source-health tests; review-only capture exporter PRs [#14](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/14) and [#15](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/15) | A genuine capture for a named, authorised run with original fetch evidence |
| Source accountability | SIP-185 register mirrored in code (176 total, 112 mandatory), checks and fallback-evidence validation | Human-confirmed per-source outcomes for **all 112** mandatory entries for that run |
| Ingest into run | Read-only manifest validation, mapping and preflight; tests | Atomic, idempotent **server-side batch import** and real two-writer test. Per-article POST is **not** an approved operator workaround |
| Candidate triage | Server-side scoring, verification, routing and exclusion paths; UI and unit/integration checks | Observed real-data scoring / verification / routing evidence, including rejected and no-signal cases |
| Report | Brief Builder UI and report version/decision workflow; seeded local UI dataset | An actual source-supported, reviewed SIP-186 daily report from a real run |
| QA / CEO / delivery | Human gates, append-only decision/audit records, manual delivery records | Run-specific independent QA, CEO approval, separate recipient-bound distribution authority and a recorded delivery **if authorised** |

Implementation ≠ operational sign-off. See [SIP-186 template](launch/SIP-186_daily_brief_template_v0.9.md), [operator guide](operator-guide.md), and [live proof checklist](LIVE_E2E_PROOF_PLAN_2026-10-27.md).

### How to show it without confusing a demonstration for production

1. **Start with this explanation and the sample output**: [illustrative Daily Intelligence Brief](ILLUSTRATIVE_DAILY_BRIEF.md). Mark every screen and document as *seeded / illustrative* when it is.
2. **Use the existing local demo only in an isolated environment.** The repository's [demo dataset](../seed-demo-dataset.md) deliberately creates synthetic `[SEED]` headlines and ten seeded runs spread across nine run states. Use `scripts/seed_demo.py` against an empty disposable database, **never** an INZBC production database. The historical 10 September recording is indexed in [demo evidence](../demo-evidence.md), but is not a current production walkthrough or an accessible public URL.
3. Show one candidate being marked **unverified / excluded**, then show what changes are required to include or verify it. Do not imply verification just because an AI generated a summary.
4. Show the Draft → QA → CEO decision → separate distribution authority boundary. If only simulated evidence is present, say *simulated*; do not click a live send.
5. Close with the evidence status from [#55](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/55): no recorded real end-to-end result as of this check. Ask Sunil to evaluate the *format and scope* of the brief, not to accept a fabricated live result.

## Sunil's decisions after seeing the brief

Record **his words** with date and owner. These questions are deliberately separate from SIP-191 launch/recipient authorisation.

| Question | Options / examples to clarify | Record |
|---|---|---|
| What intelligence matters daily? | FTA implementation, market access, bilateral policy, sector opportunities and risks, events/delegations, member issues; which are **in** or **out** | [[Sunil reply]] |
| What should the output look like? | CEO-only executive summary vs detailed analyst annex; maximum length, urgency levels, actions/owners and sources | [[Sunil reply]] |
| How frequent and when? | One daily report, only material changes, weekends/public holidays, preferred 07:00 cutoff | [[Sunil reply]] |
| Who should receive each version? | Named internal recipients, separate member summary, permitted website/public extracts; **no default audience inferred** | [[Sunil reply]] |
| Who is the analyst, independent QA reviewer and final approver? | Record actual operators / any separation-of-duties exception. Holding multiple roles does not magically create independent review | [[Sunil reply]] |
| How does he want feedback captured? | Comments on first seeded sample, followed by real sample only after run/QA evidence exists | [[Sunil reply]] |

**No model output is authorised for member/public publication by completing this table.** The report-specific approval and distribution decision remain separate.

## Separate idea: registration and members area on the website

Sunil's 27 October comment **raises an option; it does not approve a platform replacement**. The [16 October client decision](../meetings/client/2026-10-16-decision-update.md) was to keep **Member Jungle** as membership system of record and use a website link-out. [Membership design](../modules/membership-crm.md) explains why duplicating payment and consent/member registers is risky.

**Paras + Bhanu + Sunil discovery, not Roshan's SIP implementation:**
- Identify whether Sunil meant **event ticket registration**, **membership joining/renewal**, **member-only resources**, or a combination; name the current provider and today's pain/cost before selecting a replacement.
- Compare a better integrated website user journey while Member Jungle remains authoritative, versus full in-house replacement (identity, GST, payments/refunds, member migration, consent, retention, security and operational support).
- Capture an explicit revised decision before changing [#198](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/198) or [#199](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/199). Do **not** start collecting member personal data or create a second member register from an exploratory chat.

## Immediate ownership

- **Roshan:** collector mapping/source evidence, offline preview and real-run reconciliation after API readiness; #55 evidence; [FTA evaluation #393](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/393) and [literature review #387](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/387) remain separate coursework.
- **Bhanu:** reviews and merge sequence, safe batch-import API, platform deployment, authorisation and audit integration, production configuration decisions.
- **Paras:** UI demonstration, QA/review usability; event/member-site discovery (not replacement implementation without approval).
- **Sunil / INZBC:** report purpose, intended readers, role assignments, original written approval, actual QA/CEO decisions, new website scope (if any).

**Success criterion for this walkthrough:** Sunil can explain the sample report, identify what he wants changed, and distinguish implemented demo functions from a verified full SIP day. This is **not** the closure criterion for #55.
