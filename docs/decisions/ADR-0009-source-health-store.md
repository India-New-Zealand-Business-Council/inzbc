# ADR-0009: Where the collector's cross-run source health lives

**Status:** Proposed. A recommendation only. The team has not picked, so #388 stays open.
**Date:** 2026-10-14
**Deciders:** Roshan Aryal, Bhanu Gupta, Paras
**Decision owner:** the team. Roshan drafted this so the choice is written down.

## Context

News-agent pull request #14 records each source's outcome for the run that just happened. The consecutive-run counter that would mark a source stale does not survive the next run. `daily.yml` checks out `main` on an ephemeral runner. On both `main` and that pull request the schedule is commented out, and the workflow is `workflow_dispatch` only (the file dates that controlled launch to 27-31 Jul 2026). A state file written during the job is discarded with the runner.

After the review on 5 Sep 2026, `main()` on that pull request neither loads nor saves `state/source_health.json`, and `summarise_source_health` leaves the STALE line off unless `include_stale=True`. That is per-run health. It is what the code does on the pull request. It is not a store.

#388 lists three options. The detail is in `docs/source-freshness.md` on the news-agent pull request. This note does not add a fourth option, and it does not change the workflow.

## Options

### 1. Commit the state file back to main

The counter would still be there on the next checkout.

The cost is permission. The workflow would need to push to the default branch. The cron is off today. The permission would still be there when someone turns the schedule back on. A job that can push to `main` can also push a bad state file, or race a human commit. That is a decision about permissions.

### 2. actions/cache

No extra permission. The freshness doc on the pull request says a cache entry can be evicted without warning, and a reset counter under-reports a dead source. That is the failure this counter exists to catch. This recommendation rejects option 2 for that reason. It does not cite a cache policy beyond that document.

### 3. Postgres through the SIP API

This is the same place as the rest of the run record. It depends on #55, which is open. That issue says it is blocked on a live backend and the required platform configuration. Until that run exists, this store cannot be built, and it should not be described as if it were.

## Recommendation

Keep the per-run report that pull request #14 already has, with the STALE line off, until a store exists.

Do not use `actions/cache` for this counter.

Do not give the daily workflow permission to push to `main` unless the team accepts that permission in writing. This note does not make that change.

When #55 can run, store the counters in Postgres through the SIP API. That option does not forget a dead source by dropping a file or a cache entry.

## Decision

Not taken. #388 stays open until Bhanu and Paras pick an option, or say this recommendation stands.

## What this does not change

No edit to `daily.yml`. No cache. No new permission. The STALE line stays off. The news-agent pull request is not modified by this note.

## Consequences

A source that returns nothing for several real days will not be marked STALE until a store exists. The run register will keep saying what this run checked. That is the honest statement without a store.

If the team picks option 1, the follow-up is its own pull request: a workflow that can push the state file, plus a test that a second run still sees the first run's counter. If the team picks option 3, the follow-up waits on #55.
