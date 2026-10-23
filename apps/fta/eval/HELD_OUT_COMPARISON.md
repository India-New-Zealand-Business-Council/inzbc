# Held-out retrieval variant comparison (#393)

The main `questions.csv` set was used during synonym-map development, so a high score there cannot by itself demonstrate out-of-sample performance. `held_out_questions.csv` (issue #390, written by Paras) is evaluated separately for each existing retrieval variant, without changing the deployed `answer_query()` implementation.

Run `uv run python -m apps.fta.eval.variants` to print the main and held-out score summaries plus per-variant error lists. Run `uv run python -m apps.fta.eval.variants --write` to write `results/variants.json`, `results/variant_errors.json`, `results/variants-held-out.json`, `results/variant_errors-held-out.json`, and `results/held-out-overlap.json`. Never merge held-out rows into development-set totals or retune synonym mappings against held-out errors while calling it blind evidence.

**Evidence limits:** The held-out file currently covers synonym questions only; it cannot validate independent no-match accuracy, product-framing precision, or a new embedding/hybrid ranker. The variants implemented today are keyword (current deployed logic), BM25, BM25 plus synonyms, and BM25 plus synonyms and framing guard. A dense/hybrid comparison needs the #63 ownership/architecture decision and independently reviewed reference labels. No ranker deployment is authorized by this report. Validate generated report diffs and CI before merging.

## Held-out independence caveat

An exact-query audit (case-folded, whitespace-normalized) finds **2 of 10** held-out rows overlap development questions: **H03 = Q27 ('milk powder')** and **H04 = Q31 ('baby formula')**. These questions were separately authored but are *not unseen queries*, and must not be described as ten fully independent tests. The command emits a warning and writes `held-out-overlap.json` without rewriting Paras's held-out labels. Use the complete 10-row results as a historical comparison only; if reporting generalization, label the overlap and request a separately authored, non-overlapping replacement set through #390 / the tech lead rather than silently selecting a favorable subset.

The evaluator additionally writes `variants-held-out-nonoverlap.json` and `variant_errors-held-out-nonoverlap.json` for the **eight** query strings that do not occur in the development set. These are reported alongside (not in place of) the original ten-question historical results; the eight-query slice is still small and synonym-only. Do not treat the eight-query number as a broadly independent production-quality estimate.
