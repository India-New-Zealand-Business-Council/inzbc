from __future__ import annotations

import pytest

from apps.fta.corpus import CORPUS
from apps.fta.eval.run_eval import (
    Question,
    evaluate,
    first_relevant_rank,
    load_questions,
    main,
    score,
)


def _q(qid: str, expected: set[str], type_: str = "exact") -> Question:
    return Question(qid=qid, query=qid, expected_ids=frozenset(expected), type=type_)


def test_question_set_only_names_confirmed_corpus_entries() -> None:
    # An expected id that is unconfirmed can never be returned, so the question would count as a
    # miss for a reason that has nothing to do with ranking.
    confirmed = {entry.id for entry in CORPUS if entry.confirmed}
    questions = load_questions()
    assert len(questions) >= 30
    for question in questions:
        assert question.expected_ids <= confirmed, question.qid


def test_question_set_covers_every_query_type_and_has_unique_ids() -> None:
    questions = load_questions()
    assert {q.type for q in questions} == {
        "exact",
        "multi_term",
        "synonym",
        "no_match",
        "product_framing",
    }
    assert len({q.qid for q in questions}) == len(questions)
    assert all(not q.answerable for q in questions if q.type == "no_match")


def test_first_relevant_rank_is_one_based_and_none_when_absent() -> None:
    assert first_relevant_rank(["A", "B"], frozenset({"B"})) == 2
    assert first_relevant_rank(["A"], frozenset({"B"})) is None


def test_score_computes_hits_mrr_and_no_match_accuracy() -> None:
    rows = [
        (_q("1", {"A"}), ["A", "B"]),  # rank 1
        (_q("2", {"A"}), ["B", "C", "A"]),  # rank 3
        (_q("3", {"A"}), ["B"]),  # miss
        (_q("4", set(), "no_match"), []),  # correctly declined
        (_q("5", set(), "no_match"), ["B"]),  # answered when it should not
    ]
    assert score(rows) == {
        "answerable": 3,
        "unanswerable": 2,
        "hit_at_1": round(1 / 3, 4),
        "hit_at_3": round(2 / 3, 4),
        "mrr": round((1 + 1 / 3) / 3, 4),
        "no_match_accuracy": 0.5,
    }


def test_score_reports_none_for_an_empty_group() -> None:
    assert score([(_q("1", {"A"}), ["A"])])["no_match_accuracy"] is None


def test_evaluate_groups_by_type_with_a_custom_retriever() -> None:
    questions = [_q("1", {"A"}), _q("2", set(), "no_match")]
    report = evaluate(questions, retrieve=lambda query: ["A"])
    assert report["overall"]["hit_at_1"] == 1.0
    assert report["by_type"]["no_match"]["no_match_accuracy"] == 0.0
    assert report["per_question"][0]["rank"] == 1


def test_live_explainer_answers_every_exact_question_and_declines_every_no_match() -> (
    None
):
    # Exact-wording and must-decline questions are the floor any ranking change has to keep.
    report = evaluate(load_questions())
    assert report["by_type"]["exact"]["hit_at_1"] == 1.0
    assert report["by_type"]["no_match"]["no_match_accuracy"] == 1.0


def test_main_prints_summary_and_writes_report(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr("apps.fta.eval.run_eval.RESULTS_DIR", tmp_path)
    assert main(["--write", "trial"]) == 0
    assert (tmp_path / "trial.json").exists()
    assert "overall" in capsys.readouterr().out


def test_live_scores_match_the_committed_current_result() -> None:
    # results/current.json is the score of the ranker as committed. A change that moves any
    # per-type metric has to regenerate it in the same PR, so the reviewer sees the score move in
    # the diff instead of finding out later.
    import json

    from apps.fta.eval.run_eval import RESULTS_DIR

    committed = json.loads((RESULTS_DIR / "current.json").read_text(encoding="utf-8"))
    live = evaluate(load_questions())
    regenerate = "uv run python -m apps.fta.eval.run_eval --write current"

    for type_name, committed_metrics in committed["by_type"].items():
        live_metrics = live["by_type"][type_name]
        for metric, committed_value in committed_metrics.items():
            live_value = live_metrics[metric]
            if committed_value is None or live_value is None:
                assert live_value == committed_value, (type_name, metric)
                continue
            assert live_value >= committed_value, (
                f"{type_name} {metric} dropped from {committed_value} to {live_value}"
            )
            assert live_value == committed_value, (
                f"{type_name} {metric} improved to {live_value}. Record it: {regenerate}"
            )

    assert live == committed, f"Eval report changed. Record it: {regenerate}"


def test_eval_gate_rejects_stale_question_results(monkeypatch) -> None:
    live = evaluate(load_questions())
    live["per_question"][0]["returned_top3"].append("FTA-002")
    monkeypatch.setattr(__name__ + ".evaluate", lambda _: live)
    with pytest.raises(AssertionError, match="Record it"):
        test_live_scores_match_the_committed_current_result()
