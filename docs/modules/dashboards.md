# Module — Executive & board dashboards

Owner: Paras · Status: planned · Read-only views over the shared DB.

## Purpose
Turn the platform's records into decisions: executive and board views over SIP, membership,
sponsors, events and FTA activity. Reporting only — no writes.

## Executive view
Current control state · current SIP run + launch period · open Critical/High actions · active
watches · QA/distribution status · next CEO decision · exceptions · corrections · Day 5 + 30-day
review status.

## Board / measures (brief §17)
Membership: application conversion, processing time, renewal rate, portal activation.
Trade/FTA: qualified enquiries, sector-brief usage, introductions completed, recorded outcomes.
SIP: scheduled runs completed, source coverage, QA pass rate, correction rate, time-to-brief.
Sponsors/governance: benefits delivered on time, renewal rate, board-report prep time, incidents.

## Dependencies
Bhanu's DB + API + audit (source of all metrics); each module's records; INZBC baseline/target values.

## Open decisions
Reporting tool: in-app views vs Power BI (licence-dependent); baseline + target values per metric.

## Definition of done
Executive view reflects live control state; board scorecards compute from the DB; no write paths;
metrics match approved definitions.
