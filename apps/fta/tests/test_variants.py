from __future__ import annotations

import json

from apps.fta.eval import variants as variants_module
from apps.fta.eval.variants import BM25, _query_weights, compare, main, variants


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
    assert set(written) == {"keyword", "bm25", "bm25_synonyms"}
    assert "bm25_synonyms" in capsys.readouterr().out
