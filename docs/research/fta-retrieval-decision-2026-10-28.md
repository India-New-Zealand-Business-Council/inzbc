# FTA Explainer retrieval selection — evidence and conditional decision

**Date:** 28 October 2026  
**Status:** proposed engineering recommendation; **not** INZBC/technical-lead approval to change the production ranker.  
**Issue:** #393 (supports #63, #387). No new ranking code or new claims of independent evaluation.

## Decision proposed

**Keep the current keyword + curated synonyms + product-framing guard** in `apps/fta/explainer.py` for the existing confirmed FTA corpus. Do not switch production to bare BM25, BM25 with synonyms, or dense/hybrid retrieval based on these measurements. Prepare a separately labelled, broader blind set and a verified complete-ranking embedding capture before reopening this decision.

## Recorded comparison

Source files: `apps/fta/eval/results/variants.json`, `variants-held-out.json`, `variants-held-out-nonoverlap.json`, `variant_errors*.json`. Comparisons are *exactly these committed records*. They were not regenerated when this note was written on 28 October; a rerun on 20 November reproduced them exactly (see "Reproducibility check" below).

| Ranker | Development hit@1 (45 answerable) | Development no-match (10) | Held-out hit@1 (10 synonym queries) | Non-overlapping held-out hit@1 (8) |
| --- | ---: | ---: | ---: | ---: |
| Current keyword/synonyms/framing | 45/45 (100%) | 10/10 (100%) | 8/10 (80%) | 6/8 (75%) |
| BM25, no synonyms | 33/45 (73.33%) | 10/10 (100%) | 5/10 (50%) | 3/8 (37.5%) |
| BM25 + synonyms | 41/45 (91.11%) | 10/10 (100%) | 8/10 (80%) | 6/8 (75%) |
| BM25 + synonyms + framing | 45/45 (100%) | 10/10 (100%) | 8/10 (80%) | 6/8 (75%) |

The development set was used during synonym tuning. The ten held-out queries are **synonyms only**, and H03/H04 duplicate Q27/Q31 exactly. The non-overlapping eight are not enough to validate a production upgrade or no-match safety. Missing no-match measurement for held-out is **not** 100%—it is not measurable from this set. The live keyword ranker ties the strongest BM25 variant here; adding the BM25 implementation gives no documented held-out gain.

## Error analysis, preserving unfavourable cases

- The current keyword ranker misses **H07**, `visitor numbers` (expected FTA-023; no retrieved entry), and **H09**, `economic impact study` (top result FTA-022, expected FTA-018). All measured alternatives miss the same two held-out queries.
- Bare BM25 also misses H01 `logs`, H02 `crayfish`, and H05 `overseas students`; the synonym expansion repairs those on this set.
- On development, bare BM25 gets Q47–Q50 product-framing queries wrong because a generic term such as `exports` outranks a product match. The framing guard restores those cases, but cannot solve H07/H09 without new tested evidence.
- Do **not** immediately add `visitor numbers` or `economic impact study` to the synonym map: inspecting held-out failures and then editing synonyms would contaminate that held-out set and hide this limitation.
- A returned result is not the same as a supported trade/FTA answer; the Explainer must still return only confirmed, source-cited entries and escalate unsupported queries.

## Dense/hybrid status

`apps/fta/eval/hybrid.py` and `apps/fta/eval/DENSE_HYBRID.md` provide an offline protocol, **not real measured dense/hybrid scores**. A complete score capture requires each confirmed corpus entry on every question (currently 22 confirmed of 23 total according to that protocol), a canonical indexed-text hash, question/corpus fingerprints, threshold selected on development before held-out labels, and independent gateway/store-log verification. Never interpret a missing score/candidate as no-match.

A production dense/hybrid change requires: approved model/data boundary under ADR-0006, pinned model/version, independent no-match and product-framing labels, threshold calibration and precommitted evaluation, no unacceptable regression from current keyword performance, and explicit approval under #63. This note deliberately does not select a threshold or manufacture embedding measurements.

## Completion gates for issue #393

- [x] Existing lexical/BM25 variants scored in committed records, by question type, with error output.
- [x] Held-out results and exact-query overlap audit reported separately.
- [x] Proposed choice justified by the local evidence and retrieval literature (see `docs/research/retrieval-literature-review.md`).
- [ ] Independent blind no-match and product-framing questions with reviewed labels; confirm no development overlap.
- [ ] Complete real dense/hybrid snapshot and a preregistered threshold, if embeddings are approved.
- [x] Rerun/version check for the committed reports (20 November 2026, see below).
- [ ] Technical lead acceptance.

**Disposition:** keep #393 open until the outstanding acceptance criteria are evidenced. No production ranking change is implied.

## Reproducibility check, 20 November 2026

Rerun on a clean, detached worktree of `main` at `3567604`, Python 3.13.15, uv 0.12.19, with dependencies installed the way CI installs them:

    uv sync --locked --extra dev
    uv run python -m apps.fta.eval.run_eval --write current
    uv run python -m apps.fta.eval.variants --write
    uv run pytest apps/fta -q

- Both commands rewrote `current.json`, `variants.json`, `variant_errors.json`, `variants-held-out.json`, `variant_errors-held-out.json`, `variants-held-out-nonoverlap.json`, `variant_errors-held-out-nonoverlap.json` and `held-out-overlap.json`. Afterwards `git status` showed no change to any tracked file, so each regenerated report is byte-identical to the committed one.
- Every figure in the table above was recomputed from the regenerated reports and matches. The wrong-answer lists also match the error analysis: the live ranker misses H07 and H09 only; bare BM25 adds H01, H02 and H05 on held-out and gets Q47 to Q50 wrong on development.
- `baseline.json` and `synonyms.json` are snapshots of earlier rankers and were not regenerated.
- `run_eval --write current` also writes `results/current-held-out.json`. That file is not tracked and nothing reads it; its held-out figures (8/10 hit@1) equal the `keyword` row of `variants-held-out.json`. Delete it after a rerun rather than committing it.
- 154 FTA tests passed. Without `--extra dev` the tests fail to import `psycopg`; that is an install step, not a code fault.

This check covers the lexical comparison only. It adds no dense or hybrid scores and no new labels, and it does not change the decision proposed above.
