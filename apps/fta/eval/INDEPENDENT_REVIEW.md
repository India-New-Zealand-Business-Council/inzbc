# Independent review protocol for FTA expected answers

Tracks [issue #406](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/406). The review must be completed by Bhanu or Paras; this document does not claim that it has happened.

## Sampling and blinding

Review these ten existing question IDs, covering all five types: `Q01`, `Q10` (exact); `Q19`, `Q24` (multi_term); `Q28`, `Q32` (synonym); `Q37`, `Q43` (no_match); `Q47`, `Q53` (product_framing).

The reviewer should receive only the `qid`, `query`, and `type` fields from `questions.csv` and the authoritative FTA source corpus (`docs/fta-source-corpus.md`). **Do not show the reviewer `expected_ids`, the ranker's returned IDs, `current.json`, or the variant error reports before they record their own judgement.** The reviewer independently records the supported corpus IDs (or no match), the relevant source citations, and any uncertainty.

## Reconciliation

1. Bhanu or Paras compares their independently recorded answers to `expected_ids` after completing all ten checks.
2. For agreement, populate `checked_by` on the reviewed row with the actual reviewer's GitHub handle. Never fill this field merely because a row was sampled.
3. For disagreement, document the question ID, both answers, citations and resolution in #406. Correct an expectation only after the cited evidence supports the change.
4. If any expectation changes, rerun `uv run python -m apps.fta.eval.run_eval --write current` from the repository root and commit the resulting report alongside the CSV change. Run the FTA evaluation tests according to the repository test instructions.
5. Attach the reviewer identity, date, and test evidence to #406 before closing it.

## Completion gate

This protocol is preparation only. Issue #406 remains open until a second person has actually checked ten rows and recorded their identity. No evaluation metric or production readiness claim follows from this documentation alone.
