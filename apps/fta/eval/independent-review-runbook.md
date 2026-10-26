# Independent FTA reviewer packet — operator runbook

This supplements the existing [independent review protocol](INDEPENDENT_REVIEW.md); it does not authorise a reviewer or supersede that protocol.

## Before preparing any packet

1. Obtain technical-lead approval for a named independent reviewer. Check who authored each proposed question. Do **not** let the reviewer adjudicate their own question; in particular, check Q53 authorship.
2. Choose **exactly ten** questions spanning the five categories from `questions.csv`. This selection and its author checks are coordinator-private. Make a **private** CSV with the original column headers and those ten full original rows. Preserve its contents unchanged until reconciliation. Avoid placing this sample in public Git history.
3. Independently export the **confirmed** source entries and their stable `FTA-*` IDs, treatment and citations from `apps/fta/corpus.py`, reconciling them with `docs/fta-source-corpus.md`. Send the reviewer this *reference corpus*, **not** the answer key, ranker outputs, question types, review-to-QID mapping, or unconfirmed claims. The export is a human-reviewed release step, not automatically certified by this tool.

## Generate, review, reconcile

Run on the authorised ten-row sample (example paths are local, not committed):

```sh
python -m apps.fta.eval.independent_review prepare /secure/fta-ten-original.csv /secure/fta-blind.csv /secure/fta-private-mapping.csv
```

Only the `fta-blind.csv` file and the separately validated confirmed-corpus reference packet go to the reviewer. The mapping is created with mode 0600 and must remain in restricted storage. Each review row requires `reviewed_ids` (semicolon-separated `FTA-*` IDs or **NONE**), `reviewer`, `reviewed_on`, `evidence` (source citation/reason) and `uncertainty` (explicit `none` if no uncertainty). Reviewers must complete their work before unblinding. Never treat these fields alone as proof of independence.

```sh
python -m apps.fta.eval.independent_review compare /secure/fta-ten-original.csv /secure/fta-blind.csv /secure/fta-private-mapping.csv
```

Any later change to original expected IDs, query text, or question type invalidates the preparation fingerprint. Disagreements require human adjudication against the confirmed source, with both judgments retained. The script does not update `checked_by` or create a completed verification claim.

## Known limits

A copied query may still reveal its topic; shuffling and opaque IDs conceal the original row numbers and classification, not semantic meaning. The source packet must be reviewed and approved by a human separately, and a local 0600 file mode is not a substitute for OS-level access controls. Do not publish identifiable reviewer details, sample answer keys or private mappings inadvertently. No FTA production ranker or dense threshold is changed by this process.
