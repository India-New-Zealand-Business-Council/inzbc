from __future__ import annotations

import pytest

from apps.fta.corpus import CORPUS
from apps.fta.eval.run_eval import (
    HELD_OUT_CSV,
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


def test_held_out_set_is_blind_synonym_coverage_distinct_from_the_main_set() -> None:
    # #390: written without looking at explainer._SYNONYMS, so questions.csv's 1.000 synonym
    # score isn't graded against the same set the map was tuned to pass. Checked the same way
    # the main set is checked (only confirmed ids, no qid collisions) plus the one rule specific
    # to this file: every row is type "synonym", since that's the whole point of it existing.
    confirmed = {entry.id for entry in CORPUS if entry.confirmed}
    held_out = load_questions(HELD_OUT_CSV)
    main_qids = {q.qid for q in load_questions()}
    assert len(held_out) >= 10
    for question in held_out:
        assert question.expected_ids <= confirmed, question.qid
        assert question.type == "synonym", question.qid
    assert {q.qid for q in held_out}.isdisjoint(main_qids)


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ("", "no questions"),
        ("Q01,,FTA-005,exact,\n", "missing QID/query"),
        (" ,wool,FTA-005,exact,\n", "missing QID/query"),
        ("Q01,wool,FTA-005,unknown,\n", "invalid question type"),
        ("Q01,wool,,exact,\n", "no-match type and expected IDs disagree"),
        ("Q01,wool,FTA-005,no_match,\n", "no-match type and expected IDs disagree"),
        ("Q01,wool,FTA-999,exact,\n", "unknown or unconfirmed answer ID"),
        ("Q01,wool,FTA-005;FTA-005,exact,\n", "duplicate answer ID"),
        ("Q01,wool,FTA-005;,exact,\n", "blank or duplicate answer ID"),
        ("Q01,wool,FTA-005,exact,\nQ01,sheepmeat,FTA-006,exact,\n", "duplicate QID"),
        ("Q01,wool,FTA-005,exact,\nQ02, WOOL ,FTA-005,exact,\n", "duplicate QID or query"),
        ("Q01,wool,FTA-005,exact,,unexpected\n", "malformed CSV row"),
    ],
)
def test_invalid_eval_rows_fail_closed(tmp_path, rows: str, message: str) -> None:
    question_file = tmp_path / "questions.csv"
    question_file.write_text(
        "qid,query,expected_ids,type,checked_by\n" + rows,
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=message):
        load_questions(question_file)


def test_eval_loader_rejects_modified_header(tmp_path) -> None:
    question_file = tmp_path / "questions.csv"
    question_file.write_text("qid,query,type\nQ01,wool,exact\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid evaluation CSV header"):
        load_questions(question_file)


def test_eval_loader_accepts_valid_multi_id_and_no_match_labels(tmp_path) -> None:
    question_file = tmp_path / "questions.csv"
    question_file.write_text(
        "qid,query,expected_ids,type,checked_by\n"
        "Q50,dairy exports,FTA-013;FTA-014;FTA-015;FTA-016,product_framing,\n"
        "Q45,log in to the member portal,,no_match,\n",
        encoding="utf-8",
    )
    questions = load_questions(question_file)
    assert questions[0].expected_ids == frozenset(
        {"FTA-013", "FTA-014", "FTA-015", "FTA-016"}
    )
    assert questions[1].type == "no_match"
    assert not questions[1].answerable


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
