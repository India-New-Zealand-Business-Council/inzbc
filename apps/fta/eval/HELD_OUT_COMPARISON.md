# Held-out retrieval variant comparison (#393)

The main `questions.csv` set was used during synonym-map development, so a high score there cannot by itself demonstrate out-of-sample performance. `held_out_questions.csv` (issue #390, written by Paras) is evaluated separately for each existing retrieval variant, without changing the deployed `answer_query()` implementation.

Run `uv run python -m apps.fta.eval.variants` to print the main and held-out score summaries plus per-variant error lists. Run `uv run python -m apps.fta.eval.variants --write` to write `results/variants.json`, `results/variant_errors.json`, `results/variants-held-out.json`, and `results/variant_errors-held-out.json`. Never merge held-out rows into development-set totals or retune synonym mappings against held-out errors while calling it blind evidence.

**Evidence limits:** The held-out file currently covers synonym questions only; it cannot validate independent no-match accuracy, product-framing precision, or a new embedding/hybrid ranker. The variants implemented today are keyword (current deployed logic), BM25, BM25 plus synonyms, and BM25 plus synonyms and framing guard. A dense/hybrid comparison needs the #63 ownership/architecture decision and independently reviewed reference labels. No ranker deployment is authorized by this report. Validate generated report diffs and CI before merging.
