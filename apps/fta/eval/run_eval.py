"""Retrieval eval for the FTA Explainer: scores `answer_query()` against a fixed question set.

Each row in `questions.csv` names the corpus entries a correct answer should lead with
(`expected_ids`, `;`-separated, any one counts) or leaves them empty when the right answer is no
match, which routes the member to INZBC. The `type` column groups questions so a change can be
judged per kind of query, not only on one average: exact wording, multi-term, synonyms the corpus
does not use, and questions the corpus must decline.

Metrics:
- hit@1, hit@3: share of answerable questions with an expected entry in the top 1 or top 3.
- MRR: mean reciprocal rank of the first expected entry, 0 when none is returned.
- no-match accuracy: share of unanswerable questions that return `[]`.

The score is a fixed point to compare a ranking change against, so the output carries no date
and runs are byte-for-byte repeatable. Run it with:

    uv run python -m apps.fta.eval.run_eval              # print the summary
    uv run python -m apps.fta.eval.run_eval --write NAME # also save results/NAME.json
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from apps.fta.explainer import answer_query

_HERE = Path(__file__).resolve().parent
QUESTIONS_CSV = _HERE / "questions.csv"
# A second, separate question set (#390): synonym questions written by someone who has not seen
# `explainer._SYNONYMS`, so the synonym score on `questions.csv` isn't graded against questions the
# map was tuned to pass. Kept in its own file rather than appended to QUESTIONS_CSV for exactly
# that reason - mixing them back in would let a future map edit get tuned against it too.
HELD_OUT_CSV = _HERE / "held_out_questions.csv"
RESULTS_DIR = _HERE / "results"


@dataclass(frozen=True)
class Question:
    qid: str
    query: str
    expected_ids: frozenset[str]
    type: str

    @property
    def answerable(self) -> bool:
        return bool(self.expected_ids)


def load_questions(path: Path = QUESTIONS_CSV) -> list[Question]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            Question(
                qid=row["qid"],
                query=row["query"],
                expected_ids=frozenset(i for i in row["expected_ids"].split(";") if i),
                type=row["type"],
            )
            for row in csv.DictReader(handle)
        ]


def first_relevant_rank(returned: list[str], expected: frozenset[str]) -> int | None:
    """1-based rank of the first expected id in `returned`, or None if none is there."""
    for rank, entry_id in enumerate(returned, start=1):
        if entry_id in expected:
            return rank
    return None


def _ratio(numerator: float, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def score(rows: Iterable[tuple[Question, list[str]]]) -> dict[str, float | int | None]:
    """Aggregate metrics over (question, returned ids) pairs."""
    answerable = unanswerable = hit1 = hit3 = declined = 0
    reciprocal_ranks = 0.0
    for question, returned in rows:
        if question.answerable:
            answerable += 1
            rank = first_relevant_rank(returned, question.expected_ids)
            if rank is not None:
                hit1 += rank == 1
                hit3 += rank <= 3
                reciprocal_ranks += 1 / rank
        else:
            unanswerable += 1
            declined += not returned
    return {
        "answerable": answerable,
        "unanswerable": unanswerable,
        "hit_at_1": _ratio(hit1, answerable),
        "hit_at_3": _ratio(hit3, answerable),
        "mrr": _ratio(reciprocal_ranks, answerable),
        "no_match_accuracy": _ratio(declined, unanswerable),
    }


def evaluate(
    questions: list[Question],
    retrieve: Callable[[str], list[str]] | None = None,
) -> dict[str, object]:
    """Run every question through `retrieve` (the live Explainer by default) and score it."""
    if retrieve is None:
        retrieve = _explainer_ids
    rows = [(q, retrieve(q.query)) for q in questions]
    by_type: dict[str, list[tuple[Question, list[str]]]] = {}
    for row in rows:
        by_type.setdefault(row[0].type, []).append(row)
    return {
        "question_count": len(questions),
        "overall": score(rows),
        "by_type": {name: score(group) for name, group in sorted(by_type.items())},
        "per_question": [
            {
                "qid": q.qid,
                "query": q.query,
                "type": q.type,
                "expected": sorted(q.expected_ids),
                "returned_top3": returned[:3],
                "rank": first_relevant_rank(returned, q.expected_ids),
            }
            for q, returned in rows
        ],
    }


def _explainer_ids(query: str) -> list[str]:
    return [answer.id for answer in answer_query(query)]


def _summary(report: dict[str, object]) -> str:
    lines = [
        f"{'type':<12} {'n':>3} {'hit@1':>7} {'hit@3':>7} {'MRR':>7} {'no-match':>9}"
    ]
    groups = {"overall": report["overall"], **report["by_type"]}  # type: ignore[dict-item]
    for name, m in groups.items():
        n = m["answerable"] + m["unanswerable"]

        def fmt(value: float | None) -> str:
            return "-" if value is None else f"{value:.3f}"

        lines.append(
            f"{name:<12} {n:>3} {fmt(m['hit_at_1']):>7} {fmt(m['hit_at_3']):>7} "
            f"{fmt(m['mrr']):>7} {fmt(m['no_match_accuracy']):>9}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--write", metavar="NAME", help="save the full report to results/NAME.json"
    )
    args = parser.parse_args(argv)
    report = evaluate(load_questions())
    print(_summary(report))
    if args.write:
        RESULTS_DIR.mkdir(exist_ok=True)
        out = RESULTS_DIR / f"{args.write}.json"
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {out}")
    # Reported separately, never folded into the main total - see HELD_OUT_CSV's own comment on
    # why mixing it in would let a later map edit get tuned against the very set meant to catch
    # exactly that.
    if HELD_OUT_CSV.exists():
        held_out_report = evaluate(load_questions(HELD_OUT_CSV))
        print("\nHeld-out (blind) synonym set, #390:")
        print(_summary(held_out_report))
        if args.write:
            out = RESULTS_DIR / f"{args.write}-held-out.json"
            out.write_text(json.dumps(held_out_report, indent=2) + "\n", encoding="utf-8")
            print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
