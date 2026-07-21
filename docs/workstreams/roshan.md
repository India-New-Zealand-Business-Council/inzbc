# Worklog — Roshan

Role: intelligence, sources, data, FTA. Writes data into the system through the shared API. No UI.
Ordered backlog; take the top **Next up** item. Move finished items to **Done**.

## Lanes (my paths)
```
/apps/fta/**
/apps/comms/**        (service side; Paras owns the UI side)
/apps/sip/pipeline/**
/apps/sip/collector/** (integration with the daily-india-nz-news-agent repo)
```
Cross-repo: the collection engine lives in `daily-india-nz-news-agent`. Improve it there via its
own PR flow; this lane is the integration that pulls its output into SIP.

## Depends on (Bhanu's contracts)
DB schema, API contract, auth. Build against them; don't write to control-plane tables.

## Next up
- [ ] Wire the collection-engine output into SIP candidate capture via the API (run to candidates).
- [ ] Source register + per-source outcomes (Included/Context/Suppressed/Inaccessible/Excluded/No Qualifying Item) with fallback attempts recorded.
- [ ] Candidate capture: all fields (relevance, signal, confidence, verification, duplicate status, routing).
- [ ] Verification/citation controls: High/Critical claims need an official/high-confidence source; block unverified Critical.
- [ ] FTA source corpus (Tier 1 official first) + freshness/effective-date tracking.
- [ ] FTA Explainer service: sector query to sourced answer with citation + effective date + next step.

## Done
- (none yet)

## Blocked / decisions needed
- FTA sectors in scope + disclaimer wording (INZBC to confirm).
- Collection-engine secrets in the org repo (needs the values).

## Definition of done
A run opens, sources are recorded with outcomes, candidates captured and verified, and written to
the DB through the API. FTA answers cite Tier-1 sources with effective dates. No control-plane writes.

Base: main @ <short-sha> — record when you start a task; rebase if behind.
