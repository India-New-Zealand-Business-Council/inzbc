# Offline dense and hybrid retrieval evaluation (#393)

This evaluator reads **real recorded cosine similarity scores** from the server-side embedding service delivered in #432 / #63. It does not call a model provider, tune the similarity threshold, or change the production FTA Explainer. The existing keyword, BM25, and synonym comparison remains in variants.py.

## Capture contract and provenance

An authorized operator must use the pinned model through ModelGateway.embed, index the **confirmed FTA corpus** in EmbeddingService, and capture the actual ranked corpus IDs and cosine scores for every question. Use the same model throughout a snapshot. Record the source, run ID, collection time, corpus fingerprint and question fingerprint. Choose and document the score threshold **before** reading held-out labels. Never include raw member data, secrets, unpublished briefs, or model payloads.

Print fingerprints for each set with:

    uv run python -m apps.fta.eval.hybrid --questions dev --fingerprints
    uv run python -m apps.fta.eval.hybrid --questions held-out --fingerprints

The JSON schema is illustrated below. THIS EXAMPLE IS SYNTHETIC AND INCOMPLETE: it covers only one query, and therefore fails validation for the real 55-question dataset. The score and threshold are invented test values, not model measurements or a recommended cut-off.

    {
      "schema_version": 1,
      "corpus": "fta_corpus",
      "source": "ModelGateway.embed",
      "model": "text-embedding-3-small",
      "snapshot_id": "operator-provided-run-identifier",
      "captured_at": "2026-10-26T10:00:00+13:00",
      "corpus_sha256": "<fingerprint from the command above>",
      "questions_sha256": "<fingerprint from the command above>",
      "min_score": 0.7,
      "results": {
        "Q01": { "query": "wool", "hits": [{"id": "FTA-005", "score": 0.9}] }
      }
    }

Replace results with exactly one record for **every** question ID in the selected CSV. Include each retrieved confirmed entry ID at most once per question, and include its actual cosine score, even below the selected threshold. Empty hits means the service genuinely returned no candidates, not that collection failed. Record and investigate any gateway failure separately: missing responses must not masquerade as correct no-matches.

Run each set separately using its corresponding snapshot:

    uv run python -m apps.fta.eval.hybrid --questions dev --snapshot /secure/path/dev-scores.json
    uv run python -m apps.fta.eval.hybrid --questions held-out --snapshot /secure/path/held-out-scores.json

Add --write to generate the reviewed results/dense-hybrid-dev.json or results/dense-hybrid-held-out.json output. No real dense/hybrid results are committed by this change.

## Interpretation

The report includes per-question results and by-type metrics for three rankers: live keyword, dense above the preselected threshold, and hybrid reciprocal rank fusion with k=60. Unknown/unconfirmed IDs, missing/extra questions, changed query strings, mismatched fingerprints, invalid/duplicate scores and malformed rows fail closed. Hybrid does not generate FTA facts; it only fuses a lexical ranking and thresholded dense hits.

The 55 development questions helped tune the lexical synonym map, so even perfect development scores do not establish generalization. The 10 held-out questions are synonym-only; 2 repeat development queries (H03 and H04). They do not provide independent no-match or product-framing validation. We still need an independent reviewed no-match/product-framing test set, a documented threshold choice and authorization from the technical lead before production ranker changes.

Snapshot metadata is **declared by the exporter, not authenticated by this script**. Fingerprints catch stale inputs but cannot prove the scores came from the gateway; the reviewer must corroborate against the authorized service and its content-free usage logs.

All tests in test_hybrid.py use clearly labelled synthetic values. This PR makes the comparison **possible** but makes **no claim** about real dense/hybrid accuracy.
