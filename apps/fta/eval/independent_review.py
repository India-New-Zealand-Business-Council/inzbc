"""Prepare and reconcile blinded FTA answer-label reviews (#406).

Never send the original QIDs, question types, or mapping file to the reviewer.
prepare SOURCE REVIEW_CSV PRIVATE_MAPPING_CSV
compare SOURCE REVIEW_CSV PRIVATE_MAPPING_CSV
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import secrets
import sys
from datetime import date, datetime, timezone
from pathlib import Path

SOURCE_FIELDS = ("qid", "query", "expected_ids", "type", "checked_by")
REVIEW_FIELDS = ("token", "query", "reviewed_ids", "reviewer", "reviewed_on", "evidence", "uncertainty")
MAP_FIELDS = ("token", "qid", "source_sha256")


def read_rows(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or any(field not in reader.fieldnames for field in required):
            raise ValueError(f"{path}: missing required columns")
        rows = list(reader)
    return rows


def write_rows(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    # Exclusive creation prevents overwriting earlier independent evidence.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def validate_unique(rows: list[dict[str, str]], key: str, label: str) -> None:
    values = [row[key] for row in rows]
    if not values or any(not x.strip() for x in values) or len(set(values)) != len(values):
        raise ValueError(f"{label}: empty or duplicate {key}")


def _fingerprint(rows: list[dict[str, str]]) -> str:
    fields = ("qid", "query", "expected_ids", "type")
    payload = [{name: row[name] for name in fields} for row in rows]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def prepare(source: Path, review: Path, mapping: Path) -> None:
    rows = read_rows(source, SOURCE_FIELDS)
    if len(rows) != 10:
        raise ValueError("prepare requires an authorised, independent ten-question sample CSV")
    validate_unique(rows, "qid", "source")
    targets = [p.resolve() for p in (source, review, mapping)]
    if len(set(targets)) != 3 or review.exists() or mapping.exists():
        raise ValueError("source, review and mapping must be three distinct paths; outputs must be new")
    pairs = [(secrets.token_hex(16), row) for row in rows]
    # Shuffle order so CSV row position does not reveal original category blocks.
    secrets.SystemRandom().shuffle(pairs)
    review_rows = [
        {"token": token, "query": row["query"], "reviewed_ids": "",
         "reviewer": "", "reviewed_on": "", "evidence": "", "uncertainty": ""}
        for token, row in pairs
    ]
    fingerprint = _fingerprint(rows)
    map_rows = [{"token": token, "qid": row["qid"], "source_sha256": fingerprint} for token, row in pairs]
    # Keep the mapping private; only the review CSV goes to the human reviewer.
    try:
        write_rows(mapping, MAP_FIELDS, map_rows)
        try:
            write_rows(review, REVIEW_FIELDS, review_rows)
        except OSError:
            mapping.unlink()
            raise
    except Exception:
        raise


def parse_ids(value: str) -> frozenset[str]:
    parts = [item.strip() for item in value.split(";") if item.strip()]
    if len(parts) != len(set(parts)):
        raise ValueError("duplicate answer ID")
    return frozenset(parts)


def compare(source: Path, review: Path, mapping: Path) -> tuple[int, int, int]:
    original = read_rows(source, SOURCE_FIELDS)
    checked = read_rows(review, REVIEW_FIELDS)
    mapped = read_rows(mapping, MAP_FIELDS)
    for rows, key, name in [(original, "qid", "source"), (checked, "token", "review"),
                             (mapped, "token", "mapping")]:
        validate_unique(rows, key, name)
    if len(original) != 10:
        raise ValueError("compare requires the original ten-question sample")
    fingerprint = _fingerprint(original)
    if any(row["source_sha256"] != fingerprint for row in mapped):
        raise ValueError("source label fingerprint mismatch; review baseline changed")
    by_id = {row["qid"]: row for row in original}
    map_by_token = {row["token"]: row["qid"] for row in mapped}
    if set(map_by_token.values()) != set(by_id) or len(mapped) != len(original):
        raise ValueError("mapping does not cover original question IDs exactly")
    if set(map_by_token) != {row["token"] for row in checked}:
        raise ValueError("review token set differs from mapping")
    matches = disagreements = incomplete = 0
    for row in checked:
        qid = map_by_token[row["token"]]
        old = by_id[qid]
        if row["query"] != old["query"]:
            raise ValueError(f"{row['token']}: question text changed")
        answer = row["reviewed_ids"].strip()
        if (not row["reviewer"].strip() or not row["reviewed_on"].strip() or not answer
                or not row["evidence"].strip() or not row["uncertainty"].strip()):
            incomplete += 1
            continue
        try:
            date.fromisoformat(row["reviewed_on"].strip())
            if date.fromisoformat(row["reviewed_on"].strip()) > datetime.now(timezone.utc).date():
                raise ValueError("future review date")
            selected = frozenset() if answer.upper() == "NONE" else parse_ids(answer)
            if answer.upper() != "NONE" and not selected:
                raise ValueError("missing expected IDs")
        except ValueError as exc:
            raise ValueError(f"{row['token']}: invalid review: {exc}") from exc
        expected = parse_ids(old["expected_ids"])
        if selected == expected:
            matches += 1
        else:
            disagreements += 1
            print(f"DISAGREEMENT {qid}: original={';'.join(sorted(expected)) or 'NONE'} "
                  f"reviewed={';'.join(sorted(selected)) or 'NONE'}")
    return matches, disagreements, incomplete


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=("prepare", "compare"))
    parser.add_argument("source", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("mapping", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            prepare(args.source, args.review, args.mapping)
            print(f"Blinded review sheet: {args.review}; PRIVATE mapping: {args.mapping}")
            return 0
        matches, disagreements, incomplete = compare(args.source, args.review, args.mapping)
        print(f"Matches: {matches}; disagreements: {disagreements}; incomplete: {incomplete}")
        return 1 if disagreements or incomplete else 0
    except (ValueError, OSError) as exc:
        print(f"Review validation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
