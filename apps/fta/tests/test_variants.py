from __future__ import annotations

import json

from apps.fta.eval import variants as variants_module
from apps.fta.eval.variants import (
    _USES_SYNONYMS,
    BM25,
    _query_weights,
    compare,
    error_analysis,
    main,
    variants,
)


def test_bm25_scores_only_entries_sharing_a_term() -> None:
    bm25 = BM25()
    assert bm25.rank(_query_weights("wool", synonyms=False))[0] == "FTA-005"
    assert bm25.rank(_query_weights("steel pharmaceuticals", synonyms=False)) == []


def test_bm25_idf_is_positive_for_every_term() -> None:
    assert all(value > 0 for value in BM25().idf.values())


def test_synonym_expansion_reuses_the_live_map_at_the_live_weight() -> None:
    weights = _query_weights("lamb", synonyms=True)
    assert weights["lamb"] == 1.0
    assert weights["sheepmeat"] == 0.5
    assert "sheepmeat" not in _query_weights("lamb", synonyms=False)


def test_plain_bm25_still_leads_salmon_exports_with_the_overall_entry() -> None:
    assert BM25().rank(_query_weights("salmon exports", synonyms=False))[0] == "FTA-002"


def test_framing_guard_leads_with_the_product_not_the_overall_exports_entry() -> None:
    # Salmon, lamb and timber are not corpus terms. They reach an entry only through the synonym
    # map, so the guard is measured on bm25_synonyms rather than on plain BM25.
    guarded = variants()["bm25_synonyms_framing"]
    assert guarded("salmon exports")[0] == "FTA-008"
    assert guarded("tariffs on lamb exports")[0] == "FTA-006"
    assert guarded("timber trade exports")[0] == "FTA-004"
    assert guarded("dairy exports")[0] in {"FTA-013", "FTA-014", "FTA-015", "FTA-016"}
    assert variants()["bm25_synonyms"]("salmon exports")[0] == "FTA-002"


def test_framing_variant_returns_nothing_for_the_named_no_match_questions() -> None:
    guarded = variants()["bm25_synonyms_framing"]
    assert guarded("travel insurance") == []
    assert guarded("log in to the member portal") == []
    assert guarded("baby clothing") == []


def test_the_keyword_variant_is_the_live_explainer() -> None:
    from apps.fta.explainer import answer_query

    assert variants()["keyword"]("honey exports") == [
        a.id for a in answer_query("honey exports")
    ]


def test_every_variant_still_declines_every_no_match_question() -> None:
    # Whatever replaces or joins the live ranker must not start answering questions the corpus
    # does not cover.
    for name, report in compare().items():
        assert report["by_type"]["no_match"]["no_match_accuracy"] == 1.0, name


def test_main_writes_the_comparison(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(variants_module, "RESULTS_DIR", tmp_path)
    assert main(["--write"]) == 0
    written = json.loads((tmp_path / "variants.json").read_text(encoding="utf-8"))
    assert set(written) == {
        "keyword",
        "bm25",
        "bm25_synonyms",
        "bm25_synonyms_framing",
    }
    errors = json.loads((tmp_path / "variant_errors.json").read_text(encoding="utf-8"))
    assert set(errors) == set(written)
    printed = capsys.readouterr().out
    for name in written:
        assert name in printed


def test_every_variant_says_whether_it_expands_synonyms() -> None:
    # The error analysis reports matched terms under each variant's own expansion, so a new
    # variant has to declare it rather than fall back to a guess.
    assert set(_USES_SYNONYMS) == set(variants())


def _errors_by_qid(name: str) -> dict[str, dict]:
    return {row["qid"]: row for row in error_analysis(compare())[name]}


def test_error_analysis_lists_nothing_for_the_live_ranker() -> None:
    assert _errors_by_qid("keyword") == {}


def test_error_analysis_names_a_vocabulary_gap() -> None:
    # Plain BM25 has no synonym map, so "lamb" shares no term with the sheepmeat entry.
    row = _errors_by_qid("bm25")["Q28"]
    assert row["reason"] == "no_result"
    assert row["expected_matched"] == {"FTA-006": []}


def test_error_analysis_names_the_framing_term_behind_a_wrong_first_result() -> None:
    row = _errors_by_qid("bm25_synonyms")["Q47"]
    assert row["reason"] == "outranked"
    assert row["top"] == "FTA-002"
    assert row["top_matched"] == ["exports"]
    # "salmon" reaches the seafood entry only through the synonym map.
    assert row["expected_matched"] == {"FTA-008": ["seafood"]}


def test_error_analysis_flags_a_no_match_question_that_returned_an_answer() -> None:
    report = {
        "per_question": [
            {
                "qid": "X1",
                "query": "wool exports",
                "type": "no_match",
                "expected": [],
                "returned_top3": ["FTA-005"],
                "rank": None,
            }
        ]
    }
    [row] = error_analysis({"bm25": report})["bm25"]
    assert row["reason"] == "false_answer"
    assert row["top"] == "FTA-005"
    assert "wool" in row["top_matched"]


def test_held_out_comparison_is_scored_separately() -> None:
    from apps.fta.eval.run_eval import HELD_OUT_CSV, load_questions

    held_out = load_questions(HELD_OUT_CSV)
    reports = compare(question_path=HELD_OUT_CSV)
    assert len(held_out) >= 10
    assert set(reports) == set(variants())
    for name, report in reports.items():
        assert report["question_count"] == len(held_out), name
        assert {row["qid"] for row in report["per_question"]} == {
            row.qid for row in held_out
        }, name
        assert set(report["by_type"]) == {"synonym"}, name


def test_main_writes_held_out_variant_reports_without_mixing_sets(
    tmp_path, monkeypatch
) -> None:
    from apps.fta.eval.run_eval import HELD_OUT_CSV, load_questions

    monkeypatch.setattr(variants_module, "RESULTS_DIR", tmp_path)
    assert main(["--write"]) == 0
    main_report = json.loads((tmp_path / "variants.json").read_text(encoding="utf-8"))
    blind_report = json.loads(
        (tmp_path / "variants-held-out.json").read_text(encoding="utf-8")
    )
    blind_errors = json.loads(
        (tmp_path / "variant_errors-held-out.json").read_text(encoding="utf-8")
    )
    assert set(main_report) == set(blind_report) == set(blind_errors)
    for name in main_report:
        assert main_report[name]["question_count"] == len(
            variants_module.load_questions()
        )
        assert blind_report[name]["question_count"] == len(load_questions(HELD_OUT_CSV))
        assert all(
            row["qid"].startswith("H") for row in blind_report[name]["per_question"]
        )
        assert all(row["qid"].startswith("H") for row in blind_errors[name])


def test_held_out_overlap_audit_detects_case_and_whitespace_matches() -> None:
    from apps.fta.eval.run_eval import Question
    from apps.fta.eval.variants import held_out_overlap

    development = [Question("Q1", "  Milk   Powder ", frozenset({"FTA-013"}), "synonym")]
    blind = [Question("H1", "milk powder", frozenset({"FTA-013"}), "synonym"),
             Question("H2", "different question", frozenset({"FTA-013"}), "synonym")]
    assert held_out_overlap(development, blind) == [
        {"held_out_qid": "H1", "development_qid": "Q1", "query": "milk powder"}
    ]


def test_held_out_overlap_report_is_generated_and_identifies_existing_repeats(
    tmp_path, monkeypatch, capsys
) -> None:
    from apps.fta.eval.run_eval import HELD_OUT_CSV, load_questions
    from apps.fta.eval.variants import held_out_overlap

    monkeypatch.setattr(variants_module, "RESULTS_DIR", tmp_path)
    assert main(["--write"]) == 0
    overlap = json.loads((tmp_path / "held-out-overlap.json").read_text(encoding="utf-8"))
    assert overlap == held_out_overlap(load_questions(), load_questions(HELD_OUT_CSV))
    assert {row["held_out_qid"] for row in overlap} == {"H03", "H04"}
    assert "WARNING: 2 held-out rows repeat development queries" in capsys.readouterr().out
