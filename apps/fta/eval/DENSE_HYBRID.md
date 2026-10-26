# Offline dense and hybrid retrieval evaluation (#393)

This evaluator reads **real recorded cosine similarity scores** from the server-side embedding service delivered in #432 / #63. It does not call a model provider, tune the similarity threshold, or change the production FTA Explainer. The existing keyword, BM25, and synonym comparison remains in variants.py.

## Capture contract and provenance

An authorised operator must use the pinned model through ModelGateway.embed and build one `EmbeddingDocument` for each confirmed FTA entry, with `text=apps.fta.eval.hybrid.canonical_embedding_text(entry)`. This is exactly `topic + "\\n" + sector + "\\n" + treatment + "\\n" + citation`; no undocumented rewriting, whitespace variation, extra template, truncation or text masking. The index's `content_sha256` must therefore equal `indexed_text_sha256(entry)` for **each** record. Use the same model and indexed text throughout a snapshot, verifying per-record hashes against the service store read-back. Record the source, run ID, collection time, corpus fingerprint and question fingerprint. Choose and document the score threshold **before** reading held-out labels. Never include raw member data, secrets, unpublished briefs, or model payloads.

Print fingerprints for each set with:

    uv run python -m apps.fta.eval.hybrid --questions dev --fingerprints
    uv run python -m apps.fta.eval.hybrid --questions held-out --fingerprints

The JSON schema is illustrated below. THIS EXAMPLE IS SYNTHETIC AND INCOMPLETE: it covers only one query, and therefore fails validation for the real 55-question dataset. The score and threshold are invented test values, not model measurements or a recommended cut-off.

    {
      "schema_version": 2,
      "unfiltered_capture": true,
      "capture_min_score": -1.0,
      "capture_limit": 23,
      "filters": "none",
      "corpus": "fta_corpus",
      "source": "ModelGateway.embed",
      "model": "text-embedding-3-small",
      "snapshot_id": "operator-provided-run-identifier",
      "captured_at": "2026-10-26T10:00:00+13:00",
      "corpus_sha256": "<fingerprint from the command above>",
      "questions_sha256": "<fingerprint from the command above>",
      "min_score": 0.7,
      "results": {
        "Q01": { "query": "wool", "hits": [
          {"id": "FTA-005", "score": 0.9, "content_sha256": "<SHA-256 from stored EmbeddingDocument.text>"}
        ] }
      }
    }

Replace results with exactly one record for **every** question ID in the selected CSV, and record **every confirmed indexed FTA entry for every question**, including its actual cosine score and its `content_sha256`. Use the real `len([entry for entry in CORPUS if entry.confirmed])` for `capture_limit` (23 at the time this schema was written). Capture using `EmbeddingService.retrieve(corpus="fta_corpus", query=query, source=approved_prompt_source, min_score=-1.0, limit=confirmed_count, filters=RetrievalFilters())` after indexing the canonical text. **Do not use retrieve defaults**: `min_score=0.70` and `limit=10` silently omit low-score or lower-ranked entries. A truncated list, a skipped query, an index missing an entry, a mismatched digest, or an inconsistent corpus version now **fails closed**; zero candidates is not a valid full-rank snapshot. A failed gateway call must be recorded separately from a no-match: no-match is decided by the analysis threshold over the complete stored scores, never by missing fetch data.

The **question capture fingerprint** binds IDs and query strings, so the same score snapshot may be independently re-graded. A separate `labels_sha256` in the results binds each question's expected IDs and query type; changing the labels produces a different evaluation provenance even though the source scores remain unchanged. Operator-reported `model`, retrieval filters, index version, and timestamps must be checked against gateway/store logs by a reviewer.

Run each set separately using its corresponding snapshot:

    uv run python -m apps.fta.eval.hybrid --questions dev --snapshot /secure/path/dev-scores.json
    uv run python -m apps.fta.eval.hybrid --questions held-out --snapshot /secure/path/held-out-scores.json

Add --write to generate the reviewed results/dense-hybrid-dev.json or results/dense-hybrid-held-out.json output. No real dense/hybrid results are committed by this change.

## Interpretation

The report includes per-question results and by-type metrics for three rankers: live keyword, dense above the preselected threshold, and hybrid reciprocal rank fusion with k=60. Unknown/unconfirmed IDs, missing/extra questions, changed query strings, mismatched fingerprints, invalid/duplicate scores and malformed rows fail closed. Hybrid does not generate FTA facts; it only fuses a lexical ranking and thresholded dense hits.

The 55 development questions helped tune the lexical synonym map, so even perfect development scores do not establish generalization. The 10 held-out questions are synonym-only; 2 repeat development queries (H03 and H04). They do not provide independent no-match or product-framing validation. We still need an independent reviewed no-match/product-framing test set, a documented threshold choice and authorization from the technical lead before production ranker changes.

Snapshot metadata is **declared by the exporter, not authenticated by this script**. Fingerprints catch stale inputs but cannot prove the scores came from the gateway; the reviewer must corroborate against the authorized service and its content-free usage logs.

All tests in test_hybrid.py use clearly labelled synthetic values. This PR makes the comparison **possible** but makes **no claim** about real dense/hybrid accuracy.
