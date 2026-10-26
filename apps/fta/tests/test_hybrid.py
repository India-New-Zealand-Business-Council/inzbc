"""Regression tests use explicitly synthetic scores, not measured FTA results."""

from __future__ import annotations

import json

import pytest

from apps.fta.eval import hybrid
from apps.fta.eval.run_eval import Question


@pytest.fixture
def questions() -> list[Question]:
    return [
        Question("Q1", "wool", frozenset({"FTA-005"}), "exact"),
        Question("Q2", "travel insurance", frozenset(), "no_match"),
    ]


@pytest.fixture
def snapshot(questions: list[Question]) -> dict:
    return {
        "schema_version": 1,
        "corpus": "fta_corpus",
        "source": "ModelGateway.embed",
        "snapshot_id": "synthetic-test-only",
        "captured_at": "2026-10-26T00:00:00Z",
        "model": "fake-test-model",
        "min_score": 0.7,
        "corpus_sha256": hybrid.corpus_fingerprint(),
        "questions_sha256": hybrid.questions_fingerprint(questions),
        "results": {
            "Q1": {"query": "wool", "hits": [
                {"id": "FTA-005", "score": 0.9},
                {"id": "FTA-010", "score": 0.1},
            ]},
            "Q2": {"query": "travel insurance", "hits": [
                {"id": "FTA-010", "score": 0.2},
            ]},
        },
    }


def test_threshold_preserves_abstention_and_keyword_reference(
    questions: list[Question], snapshot: dict
) -> None:
    report = hybrid.evaluate_snapshot(snapshot, questions)
    assert set(report["reports"]) == {"keyword", "dense", "hybrid_rrf"}
    for name in report["reports"]:
        overall = report["reports"][name]["overall"]
        assert overall["hit_at_1"] == 1.0, name
        assert overall["no_match_accuracy"] == 1.0, name
    assert report["provenance"]["min_score"] == 0.7
    assert report["provenance"]["snapshot_id"] == "synthetic-test-only"


def test_rrf_deduplicates_and_is_stable_on_ties() -> None:
    assert hybrid.reciprocal_rank_fusion([], []) == []
    assert hybrid.reciprocal_rank_fusion(["FTA-010"], ["FTA-005"]) == [
        "FTA-005", "FTA-010"
    ]
    assert hybrid.reciprocal_rank_fusion(
        ["FTA-005", "FTA-010"], ["FTA-010", "FTA-005"]
    ) == ["FTA-005", "FTA-010"]
    with pytest.raises(ValueError, match="positive"):
        hybrid.reciprocal_rank_fusion([], [], k=0)


@pytest.mark.parametrize("alteration,match", [
    (lambda d: d.update(corpus_sha256="wrong"), "corpus fingerprint"),
    (lambda d: d.update(questions_sha256="wrong"), "question fingerprint"),
    (lambda d: d["results"].pop("Q2"), "exactly every question"),
    (lambda d: d["results"].update(Q3={}), "exactly every question"),
    (lambda d: d["results"]["Q1"].update(query="lamb"), "query text"),
    (lambda d: d.update(source="unknown"), "approved"),
    (lambda d: d.update(min_score=None), "finite cosine score"),
    (lambda d: d.update(min_score=float("nan")), "finite cosine score"),
    (lambda d: d["results"]["Q1"]["hits"].append({"id": "FTA-005", "score": 0.8}), "duplicate"),
    (lambda d: d["results"]["Q1"]["hits"].append({"id": "NOT-A-CORPUS-ID", "score": 0.8}), "unknown"),
    (lambda d: d["results"]["Q1"]["hits"][0].update(score=True), "finite cosine score"),
    (lambda d: d["results"]["Q1"]["hits"][0].update(score=1.1), "between -1 and 1"),
])
def test_snapshot_fails_closed_on_invalid_or_stale_input(
    questions: list[Question], snapshot: dict, alteration, match: str
) -> None:
    alteration(snapshot)
    with pytest.raises(ValueError, match=match):
        hybrid.evaluate_snapshot(snapshot, questions)


def test_snapshot_requires_distinct_question_text(snapshot: dict) -> None:
    duplicate = [
        Question("Q1", "wool", frozenset({"FTA-005"}), "exact"),
        Question("Q2", "wool", frozenset({"FTA-005"}), "exact"),
    ]
    snapshot["questions_sha256"] = hybrid.questions_fingerprint(duplicate)
    with pytest.raises(ValueError, match="distinct query"):
        hybrid.evaluate_snapshot(snapshot, duplicate)


def test_cli_prints_fingerprints_without_needing_a_snapshot(capsys) -> None:
    assert hybrid.main(["--questions", "dev", "--fingerprints"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["question_count"] >= 55
    assert value["corpus_sha256"] == hybrid.corpus_fingerprint()


def test_cli_writes_only_when_explicitly_requested(
    tmp_path, monkeypatch, questions: list[Question], snapshot: dict, capsys
) -> None:
    from apps.fta.eval import hybrid as module

    file_path = tmp_path / "synthetic.json"
    file_path.write_text(json.dumps(snapshot), encoding="utf-8")
    dataset = tmp_path / "questions.csv"
    dataset.write_text(
        "qid,query,expected_ids,type,checked_by\n"
        "Q1,wool,FTA-005,exact,\nQ2,travel insurance,,no_match,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "QUESTIONS_CSV", dataset)
    monkeypatch.setattr(module, "RESULTS_DIR", tmp_path / "out")
    assert module.main(["--questions", "dev", "--snapshot", str(file_path)]) == 0
    assert not (tmp_path / "out").exists()
    capsys.readouterr()
    assert module.main([
        "--questions", "dev", "--snapshot", str(file_path), "--write"
    ]) == 0
    result = json.loads((tmp_path / "out" / "dense-hybrid-dev.json").read_text())
    assert result["provenance"]["question_count"] == 2
    assert result["reports"]["hybrid_rrf"]["overall"]["no_match_accuracy"] == 1.0
