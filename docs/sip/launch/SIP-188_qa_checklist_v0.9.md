# SIP-188 QA Checklist (v0.9 Review Draft)

Independent QA before any Daily Brief reaches the CEO. Reviewer: Paras (primary) / Roshan
(backup). The reviewer must not be the run's analyst. Any Critical failure blocks release and
is not downgraded to a warning.

Run ID: __________  Reviewer: __________  Date/time: __________

## Authority and versions
- [ ] Run authority active (SIP-191), date within 27-31 Jul, operator authorised.
- [ ] Approved version set present; no uncontrolled change. (Critical if failed)

## Coverage and sources
- [ ] Coverage window is exactly 24h, Pacific/Auckland, timestamps recorded.
- [ ] Every applicable mandatory source has an outcome. (Critical if any blank)
- [ ] Inaccessible sources show fallback attempts + reason; not silently omitted.

## Content quality
- [ ] Freshness: publication vs event date checked; nothing old shown as new.
- [ ] Relevance: each item passes NZ + INZBC/member tests; no generic India news.
- [ ] Verification: every High/Critical claim has official/high-confidence evidence. (Critical)
- [ ] No High/Critical claim rests on a snippet, inaccessible article, or single weak source.
- [ ] Duplicates merged to one canonical item.
- [ ] Active Carry-Forward correctly labelled (not presented as new).
- [ ] No Material New Signal used honestly where applicable; no filler.
- [ ] Factual consistency; facts separated from analysis.

## Records and routing
- [ ] Report follows SIP-186 structure.
- [ ] Every action has an owner and due/review date; no orphaned actions.
- [ ] Register routing correct; DB is the single Action Register (not SIP-187).
- [ ] DB and tracker reconciled (IDs, owners, statuses, dates, routing, evidence). (Critical if contradictory)
- [ ] Evidence retained (append-only; no overwrite).

## Approval and distribution
- [ ] Human approval recorded before distribution. (Critical if missing)
- [ ] Distribution authority correct; recipient limited to sunilkaushalnz@gmail.com.
- [ ] No automated/member/external/website/social distribution.

## Result
- QA result: Pass / Fail
- Critical failures found: __________
- Corrections required: __________
- Reviewer signature + timestamp: __________
