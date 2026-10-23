# Independent FTA expected-answer review — proposed procedure

Related: [#406](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/406). **No reviewer is assigned by this document.** The technical lead must first authorize and designate an independent checker. This is a proposed protocol, not evidence that review occurred.

## Reviewer independence and sampling

After authorization, select ten rows spanning the five question types, checking the selected rows' authorship against the designated reviewer's prior contributions. In particular, Q53 was authored by Bhanu (commit `dcc8958`) and must not be counted as an independent check by Bhanu. Do not send the reviewer the type labels, expected IDs, ranker predictions or score reports.

A coordinator may use this *internal* candidate sample before checking reviewer independence: Q01, Q10, Q19, Q24, Q28, Q32, Q37, Q43, Q47 and Q53. This list and its stratification must not be included in the blinded review packet. Replace any self-authored item with an independently authored row of the same type before preparing the packet.

## Blinded packet

Provide only opaque question identifiers and query text in a shuffled order, plus a separate reference corpus export with each entry's `FTA-*` ID, source content and citation. Build that export from `apps/fta/corpus.py` and reconcile it to the controlling `docs/fta-source-corpus.md`. Do not include `expected_ids`, question `type`, the original QIDs (`questions.csv` numbers them in contiguous blocks by type, e.g. Q37–Q46 are all `no_match`, so a QID always reveals the label), `current.json`, or variant outputs. The reviewer records corpus IDs (possibly none), cited evidence, uncertainty, and the date *before* seeing expected labels.

## Reconciliation and evidence

1. The authorized reviewer records independent answers for all ten blinded questions.
2. Unblind only after submission, map opaque identifiers to original QIDs and compare with `expected_ids`.
3. Resolve disagreements against the authoritative source corpus, recording both judgments, citations and resolution in #406.
4. Enter the actual checker identity in `checked_by` only for rows genuinely checked independently. Never prepopulate this column.
5. If expected labels change, regenerate **all** dependent committed reports with `uv run python -m apps.fta.eval.run_eval --write current` and `uv run python -m apps.fta.eval.variants --write`, then run relevant FTA tests. Review report diffs for changed metrics and error classifications.
6. Link the reviewer authorization, sampling independence check, dated answer record, reconciliation and test evidence in #406.

**Completion gate:** #406 stays open until the authorized independent checks are complete. No claim of independent validation or production readiness is made by this document.
