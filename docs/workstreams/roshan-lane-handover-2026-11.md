# Roshan's lane: handover of open items (Week 9)

Written 23 Nov 2026 for the Week 9 handover (30 Nov to 4 Dec). Lane: intelligence and data:
FTA retrieval evaluation, SIP source and capture checks, the hourly news collector.

This note covers how to pick up each open item in my lane. Priorities, client authority and
cross-team ownership stay as recorded in
[post-handover-open-work-2026-11-04.md](../operations/post-handover-open-work-2026-11-04.md); this
note does not change them. Where an owner is not named in a recorded decision, it says
**unresolved**. Nothing here authorises a deployment, a live run, hourly collection or a ranker change.

## Open items

| Item | Status (23 Nov) | Owner | Next step | Done when |
|---|---|---|---|---|
| [#393](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/393) FTA retrieval comparison | Open, assigned to me. Live lexical ranker kept. All 8 comparison reports reproduce byte-identically ([#574](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/574)). Held-out failures H07 and H09 recorded, not patched | Me until handover; after that **unresolved** (queue lists "Intelligence / tech lead") | Independent label check (next row); real embedding snapshot only with approved model access | Independently checked labels, a real-scores comparison report, and tech-lead acceptance |
| Independent expected-answer check ([#406](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/406) protocol) | Issue closed on 23 Oct, but the checking it describes has not been done: 55 of 55 `checked_by` cells are blank | Checker **unresolved**: the tech lead designates one | Follow [INDEPENDENT_REVIEW.md](../../apps/fta/eval/INDEPENDENT_REVIEW.md) with `independent_review.py prepare` / `compare` | `checked_by` filled only for rows genuinely checked; reports regenerated if labels change |
| [#55](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/55) first SIP-184 run | Closed on 20 Nov by GitHub when #561 merged: its description said "Do not close #55", which GitHub reads as a closing keyword. The live run has not happened. The import write path stays disabled | SIP owner, approved operators, tech lead (queue P0). Reopening is the tech lead's decision | See the queue's P0 row | Recorded authority, real run ID, QA and CEO decisions, separately authorised distribution |
| [news-agent #17](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/issues/17) source health and rights | Open. 20 Nov live smoke ([news-agent #31](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/pull/31)): 8 RSS feeds healthy, 2 no recent items, PIB empty, Beehive returns HTML, MFAT and ORF 404, 4 rights-blocked feeds not contacted; all 8 GDELT queries failed | SIP source owner (queue P1) | Confirm official working URLs, decide publisher rights, rerun the read-only smoke | Per-source evidence and an accepted fallback for each failure |
| [#509](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/509) hourly collection decision | Open. Schedule commented out in `hourly-collection.yml` | SIP owner / CEO (queue P1) | INZBC signs the decision fields | Signed #509 and a separate activation PR |
| [news-agent #11](https://github.com/India-New-Zealand-Business-Council/daily-india-nz-news-agent/issues/11) missing sheet tab | Open | Sunil (listed as a Sunil-owned action in the 19 Nov handover update) | Create `Production_Run_Register` or approve auto-creation | Daily run finds the tab |

## How to resume

### FTA evaluation (rerun and verify)

On a clean checkout of `main`:

```
uv sync --locked --extra dev
uv run python -m apps.fta.eval.run_eval --write current
uv run python -m apps.fta.eval.variants --write
uv run pytest apps/fta -q
git status
```

Expect all FTA tests to pass and `git status` to show no tracked change (the reports are
byte-identical). `run_eval` also writes an untracked `results/current-held-out.json`; it has no
consumers. Decision record: [fta-retrieval-decision-2026-10-28.md](../research/fta-retrieval-decision-2026-10-28.md).
Do not add synonyms for held-out failures after reading them; that contaminates the held-out set.

### News collector live smoke (read-only)

In `daily-india-nz-news-agent`, run the `hourly-collection.yml` workflow manually with
`run_live_smoke=true`, `run_poll=false`, `bootstrap_state=false`. Nothing is stored, sent or
published. Polling also requires the repository variable `SIP_HOURLY_COLLECTION_APPROVED`, which must
stay unset until #509 is signed. Download the evidence JSON before the 14-day artifact expiry and
record it as in news-agent #31.

### SIP import path

The atomic audited importer and its checks (#526 to #540, restored in #561) run on synthetic data
only. Production writes stay disabled until #55's gates are met. The acceptance check for #526 to
#539 is in [sip-issue-acceptance-check-2026-11-19.md](../sip/sip-issue-acceptance-check-2026-11-19.md).

## Lessons for whoever picks this up

- Reference issues with `Refs #N` only. Any phrase containing "close #N", "fixes #N" or "resolves #N",
  including "Do not close #N", closes the issue on merge.
- Prefer focused independent pull requests when feasible. For genuinely dependent changes, follow the
  documented stacked-PR rebase/retarget procedure in CONTRIBUTING.md and validate the combined result
  after each merge; do not assume stacked CI covers the final `main` integration. On 10 Nov the merged
  result lost importer validation and tests until #561 restored them.
