# INZBC AIOS: handover status update for Sunil, 19 November 2026

**Prepared by:** Roshan Aryal. **Status:** engineering status note for tech-lead review before it is
shared with Sunil. It does not change the scope accepted at the
[4 November final handover](../final-handover-2026-11-04.md), and it is not a deployment approval,
a SIP run record or a sign-off. **Tracking:** [#521](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/521).

Every statement below was checked against GitHub on 19 November 2026 (Pacific/Auckland), and
rechecked on 20 November after the tech lead's merges that morning.

## 1. What has changed since 4 November

On 10 November the tech lead merged the work queued in the
[4 November open-work register](post-handover-open-work-2026-11-04.md):

- **SIP import safety (inzbc #497, #500, #529, #540 and related PRs):** the bulk importer is in the
  code, but it is disabled by construction. It refuses to write unless a run is marked
  `production_enabled` by an authorised user. No production import has happened.
- **News collection engine (news-agent #14, #15, #16, #19, #20, #22, #24, #25):** source freshness,
  review-only capture and the hourly collector design are merged. **Both schedules are off**
  (`daily.yml` and `hourly-collection.yml` have their cron lines commented out), so nothing collects
  news automatically.
- **Operational sign-offs (#544, #546):** the documents now place operational sign-offs with Sunil and
  separate the FTA pilot from staff deployment.
- On 17 November issues #493 and #523 (inzbc) and #18, #21 and #23 (news-agent) were closed because
  the fixes behind them had merged.
- On 20 November the tech lead merged news-agent
  [#26](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/26)
  (fail closed on invalid source-health timestamps) and
  [#30](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/30)
  (the daily run now uses the hourly feed list and skips publishers still awaiting rights permission).
  The news-agent test suite passes on `main` (196 tests, run locally on 20 November). Both schedules
  are still off.

## 2. What is still open on the engineering side

| Item | State on 20 Nov | Who acts |
|---|---|---|
| `main` does not build | The `sip-ui` build fails on a type error in `apps/comms/ui/src/components/CommsAssistant.tsx`, so every open PR shows failing frontend and end-to-end checks. The tech lead added the fix (`fix(ci): restore Comms state transitions`) to #561 on 20 November; `main` builds again once #561 merges | Tech lead merges #561 |
| [#561](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/561) | Restores importer validation and six regression tests lost after #540, plus the Comms build fix above. All nine checks pass | Tech lead review |
| [#562](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/562) | Literature review source checks (#387), draft | Roshan, then tech lead |
| [#510](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/510) | Agent UI follow-through, open | Assigned UI owner |
| SIP issues [#526](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/526), [#528](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/528), [#530](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/530), [#531](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/531), [#535](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/535), [#536](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/536), [#539](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/539) | Open. Checked item by item in the [SIP acceptance check](../sip/sip-issue-acceptance-check-2026-11-19.md): most were built by the 10 Nov merges; #535 had an audit gap, fixed in [#564](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/564); #539 waits on full CI | Tech lead reviews #561, #564 and the check |
| [#393](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/393) FTA retrieval comparison | Needs authorised real embedding scores and independently labelled test questions | Tech lead and an independent checker |

**Correction to the 4 November register:** it lists #60 (Comms review UI) as open work, but
[issue #60](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/60) was closed on
18 August, while the final handover says no reviewer screen was built. The issue state and the
handover disagree; the tech lead should confirm which is right.

## 3. What only Sunil or INZBC can do

None of these can be completed by the student team. Each needs a recorded decision or action by
the account owner.

1. **Hosting ([#99](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/99)).** No
   hosted service exists; the API and platform screens run locally only. INZBC decides whether to
   create an INZBC-owned service, its budget and who holds the account.
2. **First real SIP run ([#55](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/55)).**
   Needs SIP-191 authority on record, the approved operators, the full mandatory-source check, and
   QA and CEO decisions. Until then no production run should be described as done.
3. **Hourly news polling ([#509](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/509)).**
   The decision fields (approval, retention, owners) are unsigned. The schedule stays off until they
   are signed and a separate activation change is reviewed.
4. **Source rights ([news-agent #17](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/issues/17)).**
   Publisher permissions for Scoop and the Indian Express are not cleared, and some official feeds
   need confirmed working addresses.
5. **Backup and restore.** A timed restore of a real backup has not been done. Someone at INZBC
   needs to own a restore rehearsal; no recovery time should be quoted until then.
6. **Comms inputs policy ([#303](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/303))
   and website forms ([#45](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/45)).**
   Both need an approved privacy and data policy before anything is switched on.
7. **Written acceptance record.** The final handover reports Sunil's acceptance; the original
   written record should be filed privately by INZBC and linked from #521.
8. **Future modules.** Member portal (#198), events (#199), sponsors (#200), newsletter (#193) and
   sector briefs (#194) are proposals, not commitments. Sunil sets their priority.

## 4. What this note does not claim

- No production deployment, live SIP run, real-backup restore or client UAT has taken place since
  4 November.
- A merged PR or a passing check is engineering evidence only. It is not an approval to operate.
- The test counts in the final handover (1,398 passed, 225 skipped without a database) have not been
  re-run for this note.
