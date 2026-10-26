"""Prepare and reconcile independently checked FTA expected-answer labels.

Generate a blind sheet without the original answers:
    python -m apps.fta.eval.independent_review prepare questions.csv blind.csv

The reviewer independently fills reviewed_ids, reviewer and reviewed_on (YYYY-MM-DD).
Compare only *after* review, without modifying the source labels:
    python -m apps.fta.eval.independent_review compare questions.csv blind.csv

Exit status is nonzero for malformed or incomplete reviews and for disagreements.
This script never marks the original checked_by field as verified.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

REVIEW_FIELDS = ("qid", "query", "type", "reviewed_ids", "reviewer", "reviewed_on")
SOURCE_FIELDS = ("qid", "query", "expected_ids", "type", "checked_by")


def read_rows(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or any(field not in reader.fieldnames for field in required):
            raise ValueError(f"{path}: missing required columns")
        rows = list(reader)
    ids = [row["qid"] for row in rows]
    if not rows or any(not qid.strip() for qid in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"{path}: empty or duplicate question IDs")
    return rows


def prepare(source: Path, destination: Path) -> None:
    rows = read_rows(source, SOURCE_FIELDS)
    if destination.resolve() == source.resolve() or destination.exists():
        raise ValueError("destination must be a new file, separate from the source")
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({"qid": row["qid"], "query": row["query"], "type": row["type"],
                             "reviewed_ids": "", "reviewer": "", "reviewed_on": ""})


def parse_ids(value: str) -> frozenset[str]:
    ids = [part.strip() for part in value.split(";") if part.strip()]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate IDs")
    return frozenset(ids)


def compare(source: Path, review: Path) -> tuple[int, int, int]:
    expected = read_rows(source, SOURCE_FIELDS)
    reviewed = read_rows(review, REVIEW_FIELDS)
    source_by_id = {row["qid"]: row for row in expected}
    if set(source_by_id) != {row["qid"] for row in reviewed}:
        raise ValueError("review IDs differ from source IDs")
    matches = disagreements = incomplete = 0
    for row in reviewed:
        original = source_by_id[row["qid"]]
        if row["query"] != original["query"] or row["type"] != original["type"]:
            raise ValueError(f"{row['qid']}: query/type changed since sheet generation")
        if not row["reviewer"].strip() or not row["reviewed_on"].strip() or not row["reviewed_ids"].strip():
            # A no-match judgment must be explicitly written as NONE, not left blank.
            incomplete += 1
            continue
        try:
            date.fromisoformat(row["reviewed_on"].strip())
            supplied = (frozenset() if row["reviewed_ids"].strip().upper() == "NONE"
                        else parse_ids(row["reviewed_ids"]))
            if row["reviewed_ids"].strip().upper() != "NONE" and not supplied:
                raise ValueError("missing expected IDs")
        except ValueError as exc:
            raise ValueError(f"{row['qid']}: invalid review date or IDs: {exc}") from exc
        prior = parse_ids(original["expected_ids"])
        if supplied == prior:
            matches += 1
        else:
            disagreements += 1
            print(f"DISAGREEMENT {row['qid']}: original={';'.join(sorted(prior)) or 'NONE'} "
                  f"independent={';'.join(sorted(supplied)) or 'NONE'}")
    return matches, disagreements, incomplete


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=("prepare", "compare"))
    parser.add_argument("source", type=Path)
    parser.add_argument("review", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            prepare(args.source, args.review)
            print(f"Created blinded sheet: {args.review}")
            return 0
        matches, disagreements, incomplete = compare(args.source, args.review)
        print(f"Matches: {matches}; disagreements: {disagreements}; incomplete: {incomplete}")
        return 1 if disagreements or incomplete else 0
    except (ValueError, OSError) as exc:
        print(f"Review validation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
