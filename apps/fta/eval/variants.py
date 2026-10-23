"""Score alternative FTA rankers on the same eval questions, side by side (#393).

The live Explainer is one ranker. Choosing what replaces or joins it under #63 should rest on how
each candidate does on our own questions, by question type, not on general benchmarks. This module
holds those candidates. None of them is wired into `answer_query()`; they exist to be measured.

Every variant searches the same text the live ranker does (each confirmed entry's topic and
sector), uses the same tokeniser and stopwords, and returns only entries scoring above zero, so a
question with no shared term still comes back empty and routes to INZBC.

- `keyword`: the live `answer_query()`, as committed.
- `bm25`: Okapi BM25 (Robertson & Zaragoza, 2009) over topic plus sector, no synonym map.
- `bm25_synonyms`: BM25 with the query expanded through the live synonym map, expanded terms at
  the same half weight the live ranker gives them.
- `bm25_synonyms_framing`: the same scores as `bm25_synonyms`, ordered with the live ranker's
  framing-term guard (#402). A hit on a term outside `_FRAMING_TERMS` sorts ahead of a score
  built only from framing terms. `k1` and `b` stay at `BM25_K1` and `BM25_B`. The 2009 account
  of those constants was not re-read for this measurement.

`error_analysis()` lists every question a variant gets wrong and why: which query terms the
wrongly ranked entry matched, or that the expected entry shares no query term at all.

    uv run python -m apps.fta.eval.variants              # print the comparison
    uv run python -m apps.fta.eval.variants --write      # also save variants.json and
                                                         # variant_errors.json
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from collections.abc import Callable

from apps.fta import explainer
from apps.fta.corpus import CORPUS, TariffOutcome
from apps.fta.eval.run_eval import HELD_OUT_CSV, RESULTS_DIR, evaluate, load_questions

# The usual defaults. With one short topic and sector per entry, length normalisation (b) has
# little to work on, which is itself a finding worth recording rather than tuning away.
BM25_K1 = 1.2
BM25_B = 0.75


def _tokens(text: str) -> list[str]:
    """Same tokeniser and stopwords as the live ranker, but keeping repeats for term frequency."""
    return [
        word
        for word in explainer._WORD_RE.findall(text.lower())
        if word not in explainer._STOPWORDS
    ]


def _document(entry: TariffOutcome) -> list[str]:
    return _tokens(entry.topic) + _tokens(entry.sector)


class BM25:
    """Okapi BM25 over the confirmed corpus entries."""

    def __init__(self, k1: float = BM25_K1, b: float = BM25_B) -> None:
        self.k1 = k1
        self.b = b
        self.entries = [entry for entry in CORPUS if entry.confirmed]
        self.term_counts = [Counter(_document(entry)) for entry in self.entries]
        lengths = [sum(counts.values()) for counts in self.term_counts]
        self.lengths = lengths
        self.average_length = sum(lengths) / len(lengths)
        document_frequency: Counter[str] = Counter()
        for counts in self.term_counts:
            document_frequency.update(counts.keys())
        total = len(self.entries)
        # The "+1" form of BM25 IDF stays positive even for a term in most entries.
        self.idf = {
            term: math.log((total - df + 0.5) / (df + 0.5) + 1)
            for term, df in document_frequency.items()
        }

    def _term_score(self, term: str, index: int) -> float:
        frequency = self.term_counts[index].get(term, 0)
        if not frequency:
            return 0.0
        length_ratio = self.lengths[index] / self.average_length
        denominator = frequency + self.k1 * (1 - self.b + self.b * length_ratio)
        return self.idf[term] * frequency * (self.k1 + 1) / denominator

    def rank(
        self, weighted_terms: dict[str, float], *, framing_guard: bool = False
    ) -> list[str]:
        # Subject terms follow answer_query: every weighted query term except the framing set.
        # The guard only reorders. A zero score is still dropped, so a question that shares no
        # term stays empty. With the guard off, every row shares the first sort key.
        subject_terms = set(weighted_terms) - explainer._FRAMING_TERMS
        scored: list[tuple[bool, float, str]] = []
        for index, entry in enumerate(self.entries):
            score = sum(
                weight * self._term_score(term, index)
                for term, weight in weighted_terms.items()
            )
            if score > 0:
                framing_only = framing_guard and not bool(
                    subject_terms & self.term_counts[index].keys()
                )
                scored.append((framing_only, score, entry.id))
        scored.sort(key=lambda pair: (pair[0], -pair[1], pair[2]))
        return [entry_id for _framing_only, _score, entry_id in scored]


def _query_weights(query: str, *, synonyms: bool) -> dict[str, float]:
    terms = set(_tokens(query))
    weights = {term: 1.0 for term in terms}
    if synonyms:
        for term in explainer._expanded_keywords(terms):
            weights[term] = explainer._SYNONYM_WEIGHT
    return weights


# Whether each variant expands the query through the synonym map. The error analysis uses this to
# say which query terms an entry matched under that variant.
_USES_SYNONYMS = {
    "keyword": True,
    "bm25": False,
    "bm25_synonyms": True,
    "bm25_synonyms_framing": True,
}


def variants() -> dict[str, Callable[[str], list[str]]]:
    bm25 = BM25()
    return {
        "keyword": lambda query: [
            answer.id for answer in explainer.answer_query(query)
        ],
        "bm25": lambda query: bm25.rank(_query_weights(query, synonyms=False)),
        "bm25_synonyms": lambda query: bm25.rank(_query_weights(query, synonyms=True)),
        "bm25_synonyms_framing": lambda query: bm25.rank(
            _query_weights(query, synonyms=True), framing_guard=True
        ),
    }


def compare(*, question_path=None) -> dict[str, dict[str, object]]:
    """Compare all variants on exactly one question set, without combining held-out scores."""
    questions = load_questions(question_path) if question_path is not None else load_questions()
    return {
        name: evaluate(questions, retrieve) for name, retrieve in variants().items()
    }


def _matched_terms(query: str, entry_id: str, *, synonyms: bool) -> list[str]:
    """Query terms (after any synonym expansion) that appear in an entry's topic or sector."""
    entry = next(entry for entry in CORPUS if entry.id == entry_id)
    document = set(_document(entry))
    return sorted(
        term for term in _query_weights(query, synonyms=synonyms) if term in document
    )


def _reason(question: dict, synonyms: bool) -> dict[str, object]:
    query = question["query"]
    returned = question["returned_top3"]
    expected = question["expected"]
    if question["type"] == "no_match":
        return {
            "reason": "false_answer",
            "top": returned[0],
            "top_matched": _matched_terms(query, returned[0], synonyms=synonyms),
        }
    expected_matched = {
        entry_id: _matched_terms(query, entry_id, synonyms=synonyms)
        for entry_id in expected
    }
    if not returned:
        return {"reason": "no_result", "expected_matched": expected_matched}
    return {
        # "outranked": an expected entry is in the top three, just not first. "missed": none is.
        "reason": "outranked" if question["rank"] is not None else "missed",
        "top": returned[0],
        "top_matched": _matched_terms(query, returned[0], synonyms=synonyms),
        "expected_matched": expected_matched,
    }


def error_analysis(
    reports: dict[str, dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    """Every question each variant gets wrong, with the terms behind the wrong ranking.

    Wrong means an answerable question whose first result is not an expected entry, or a
    no-match question that returned anything.
    """
    errors: dict[str, list[dict[str, object]]] = {}
    for name, report in reports.items():
        synonyms = _USES_SYNONYMS[name]
        rows = []
        for question in report["per_question"]:  # type: ignore[attr-defined]
            if question["type"] == "no_match":
                wrong = bool(question["returned_top3"])
            else:
                wrong = question["rank"] != 1
            if wrong:
                rows.append(
                    {
                        "qid": question["qid"],
                        "query": question["query"],
                        "type": question["type"],
                        "expected": question["expected"],
                        "returned_top3": question["returned_top3"],
                        **_reason(question, synonyms),
                    }
                )
        errors[name] = rows
    return errors


def _errors_summary(errors: dict[str, list[dict[str, object]]]) -> str:
    lines = []
    for name, rows in errors.items():
        lines.append(f"{name}: {len(rows)} wrong")
        for row in rows:
            detail = (
                f"top {row['top']} on {row['top_matched']}"
                if "top" in row
                else "nothing"
            )
            lines.append(f"  {row['qid']} {row['query']!r} {row['reason']}: {detail}")
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def _summary(reports: dict[str, dict[str, object]]) -> str:
    # Wide enough for `bm25_synonyms_framing`.
    name_width = 22
    lines = [
        f"{'variant':<{name_width}} {'type':<16} {'hit@1':>6} {'MRR':>6} {'no-match':>9}"
    ]
    for name, report in reports.items():
        groups = {"overall": report["overall"], **report["by_type"]}  # type: ignore[dict-item]
        for type_name, m in groups.items():
            lines.append(
                f"{name:<{name_width}} {type_name:<16} {_fmt(m['hit_at_1']):>6} "
                f"{_fmt(m['mrr']):>6} {_fmt(m['no_match_accuracy']):>9}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--write", action="store_true", help="save results/variants.json"
    )
    args = parser.parse_args(argv)
    reports = compare()
    errors = error_analysis(reports)
    print(_summary(reports))
    print("\n" + _errors_summary(errors))
    # Keep blind questions outside the development-set totals and reports. This comparison is
    # descriptive evidence only; it is not permission to tune the synonym map on held-out rows.
    held_out_reports = None
    held_out_errors = None
    if HELD_OUT_CSV.exists():
        held_out_reports = compare(question_path=HELD_OUT_CSV)
        held_out_errors = error_analysis(held_out_reports)
        print("\nHeld-out questions (#390), separately scored:")
        print(_summary(held_out_reports))
        print("\n" + _errors_summary(held_out_errors))
    if args.write:
        RESULTS_DIR.mkdir(exist_ok=True)
        for filename, data in (
            ("variants.json", reports),
            ("variant_errors.json", errors),
        ):
            out = RESULTS_DIR / filename
            out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print(f"\nwrote {out}")
        if held_out_reports is not None and held_out_errors is not None:
            for filename, data in (
                ("variants-held-out.json", held_out_reports),
                ("variant_errors-held-out.json", held_out_errors),
            ):
                out = RESULTS_DIR / filename
                out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
