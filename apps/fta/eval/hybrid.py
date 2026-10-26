"""Offline dense and hybrid FTA retrieval comparison (#393).

Consumes recorded cosine scores from the approved server-side embedding service.
Does not call providers, invent missing hits, tune thresholds or alter production.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from apps.fta.corpus import CORPUS
from apps.fta.eval.run_eval import (
    HELD_OUT_CSV,
    QUESTIONS_CSV,
    RESULTS_DIR,
    Question,
    evaluate,
    load_questions,
)
from apps.fta.explainer import answer_query

RRF_K = 60
CAPTURE_MIN_SCORE = -1.0


def canonical_embedding_text(entry: object) -> str:
    """Frozen FTA v1 text representation used for both indexing and verification.

    Operators must index *this exact text*, not an undocumented concatenation.
    A text-only change invalidates every old dense snapshot.
    """
    return f"{entry.topic}\n{entry.sector}\n{entry.treatment}\n{entry.citation}"


def indexed_text_sha256(entry: object) -> str:
    return hashlib.sha256(canonical_embedding_text(entry).encode("utf-8")).hexdigest()


def labels_fingerprint(questions: list[Question]) -> str:
    return _digest([
        {"qid": q.qid, "expected_ids": sorted(q.expected_ids), "type": q.type}
        for q in questions
    ])


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def corpus_fingerprint() -> str:
    """Fingerprint of the retrieval fields in confirmed FTA corpus entries."""
    return _digest(
        [
            {"id": entry.id, "content_sha256": indexed_text_sha256(entry)}
            for entry in CORPUS
            if entry.confirmed
        ]
    )


def questions_fingerprint(questions: list[Question]) -> str:
    return _digest([{"qid": q.qid, "query": q.query} for q in questions])


def _finite_score(value: object, name: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite cosine score")
    score = float(value)
    if not -1.0 <= score <= 1.0:
        raise ValueError(f"{name} must be between -1 and 1")
    return score


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _ranked_dense(
    snapshot: dict[str, Any], questions: list[Question]
) -> tuple[dict[str, list[str]], float]:
    """Validate the complete snapshot before returning any ranked results."""
    if snapshot.get("schema_version") != 2:
        raise ValueError("unsupported dense snapshot schema_version")
    if snapshot.get("corpus") != "fta_corpus":
        raise ValueError("snapshot corpus must be fta_corpus")
    _text(snapshot.get("model"), "model")
    _text(snapshot.get("snapshot_id"), "snapshot_id")
    _text(snapshot.get("captured_at"), "captured_at")
    if snapshot.get("source") != "ModelGateway.embed":
        raise ValueError("source must identify the approved ModelGateway.embed path")
    if snapshot.get("corpus_sha256") != corpus_fingerprint():
        raise ValueError("corpus fingerprint mismatch; re-capture scores on this corpus")
    if snapshot.get("questions_sha256") != questions_fingerprint(questions):
        raise ValueError("question fingerprint mismatch; re-capture scores for this set")
    confirmed = {entry.id: entry for entry in CORPUS if entry.confirmed}
    if snapshot.get("unfiltered_capture") is not True:
        raise ValueError("snapshot must declare unfiltered capture")
    if snapshot.get("capture_min_score") != CAPTURE_MIN_SCORE:
        raise ValueError("capture_min_score must be -1.0")
    if snapshot.get("capture_limit") != len(confirmed):
        raise ValueError("capture limit must equal the entire confirmed corpus")
    if snapshot.get("filters") != "none":
        raise ValueError("capture must have no metadata or exclusion filters")

    threshold = _finite_score(snapshot.get("min_score"), "min_score")
    rows = snapshot.get("results")
    if not isinstance(rows, dict):
        raise TypeError("results must be a map keyed by question id")
    expected_qids = {q.qid for q in questions}
    if len(expected_qids) != len(questions):
        raise ValueError("evaluation question IDs must be unique")
    if set(rows) != expected_qids:
        raise ValueError("snapshot must contain exactly every question ID (no extras)")
    if len({q.query for q in questions}) != len(questions):
        raise ValueError("evaluation questions must have distinct query text")
    confirmed_ids = set(confirmed)

    result: dict[str, list[str]] = {}
    for question in questions:
        record = rows[question.qid]
        if not isinstance(record, dict) or record.get("query") != question.query:
            raise ValueError(f"{question.qid}: query text differs from evaluation CSV")
        hits = record.get("hits")
        if not isinstance(hits, list):
            raise TypeError(f"{question.qid}: hits must be a list")
        if len(hits) != len(confirmed_ids):
            raise ValueError(f"{question.qid}: truncated or missing dense candidates")
        seen: set[str] = set()
        scored: list[tuple[float, str]] = []
        for hit in hits:
            if not isinstance(hit, dict):
                raise TypeError(f"{question.qid}: invalid hit")
            entry_id = hit.get("id")
            if not isinstance(entry_id, str) or entry_id not in confirmed_ids:
                raise ValueError(f"{question.qid}: unconfirmed or unknown corpus id")
            if entry_id in seen:
                raise ValueError(f"{question.qid}: duplicate corpus id")
            if hit.get("content_sha256") != indexed_text_sha256(confirmed[entry_id]):
                raise ValueError(f"{question.qid}: indexed text digest mismatch")
            seen.add(entry_id)
            score = _finite_score(hit.get("score"), f"{question.qid} score")
            if score >= threshold:
                scored.append((score, entry_id))
        # Stable ties; never trust arbitrary input ordering for RRF.
        scored.sort(key=lambda item: (-item[0], item[1]))
        if seen != confirmed_ids:
            raise ValueError(f"{question.qid}: incomplete dense candidates")
        result[question.query] = [entry_id for _, entry_id in scored]
    return result, threshold


def reciprocal_rank_fusion(
    lexical: list[str], dense: list[str], *, k: int = RRF_K
) -> list[str]:
    """RRF over two ranked lists, preserving abstention if both are empty."""
    if k <= 0:
        raise ValueError("RRF k must be positive")
    scores: dict[str, float] = {}
    for ranking in (lexical, dense):
        for rank, entry_id in enumerate(ranking, start=1):
            scores[entry_id] = scores.get(entry_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda entry_id: (-scores[entry_id], entry_id))


def evaluate_snapshot(
    snapshot: dict[str, Any], questions: list[Question]
) -> dict[str, object]:
    """Evaluate a single question set; never mix development and held-out rows."""
    dense, threshold = _ranked_dense(snapshot, questions)

    def lexical(query: str) -> list[str]:
        return [answer.id for answer in answer_query(query)]

    return {
        "provenance": {
            "snapshot_sha256": _digest(snapshot),
            "snapshot_id": snapshot["snapshot_id"],
            "captured_at": snapshot["captured_at"],
            "source": snapshot["source"],
            "model": snapshot["model"],
            "corpus_sha256": snapshot["corpus_sha256"],
            "questions_sha256": snapshot["questions_sha256"],
            "labels_sha256": labels_fingerprint(questions),
            "indexed_text_version": "fta-v1-topic-sector-treatment-citation",
            "capture_min_score": CAPTURE_MIN_SCORE,
            "capture_limit": len([entry for entry in CORPUS if entry.confirmed]),
            "min_score": threshold,
            "rrf_k": RRF_K,
            "question_count": len(questions),
            "note": "Snapshot metadata is exporter-declared, not independently authenticated.",
        },
        "reports": {
            "keyword": evaluate(questions, lexical),
            "dense": evaluate(questions, lambda query: dense[query]),
            "hybrid_rrf": evaluate(
                questions,
                lambda query: reciprocal_rank_fusion(lexical(query), dense[query]),
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--questions", choices=("dev", "held-out"), required=True)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--fingerprints", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    questions_path = QUESTIONS_CSV if args.questions == "dev" else HELD_OUT_CSV
    questions = load_questions(questions_path)
    if args.fingerprints:
        print(json.dumps({
            "corpus_sha256": corpus_fingerprint(),
            "questions_sha256": questions_fingerprint(questions),
            "labels_sha256": labels_fingerprint(questions),
            "capture_min_score": CAPTURE_MIN_SCORE,
            "capture_limit": len([entry for entry in CORPUS if entry.confirmed]),
            "question_count": len(questions),
        }, indent=2))
        return 0
    if args.snapshot is None:
        parser.error("--snapshot is required unless --fingerprints is supplied")
    with args.snapshot.open(encoding="utf-8") as handle:
        snapshot = json.load(handle)
    if not isinstance(snapshot, dict):
        raise TypeError("snapshot must be a JSON object")
    report = evaluate_snapshot(snapshot, questions)
    print(json.dumps({
        "provenance": report["provenance"],
        "metrics": {
            name: variant["overall"]
            for name, variant in report["reports"].items()
        },
    }, indent=2))
    if args.write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        target = RESULTS_DIR / f"dense-hybrid-{args.questions}.json"
        target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
