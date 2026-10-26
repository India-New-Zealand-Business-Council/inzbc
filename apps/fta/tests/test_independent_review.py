"""Regression tests for blind FTA label verification (#406)."""
import csv
from pathlib import Path

import pytest

from apps.fta.eval.independent_review import compare, prepare


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def source(tmp_path: Path) -> Path:
    path = tmp_path / "original.csv"
    write_csv(path, ["qid", "query", "expected_ids", "type", "checked_by"], [
        {"qid": "Q1", "query": "wool", "expected_ids": "FTA-005", "type": "exact", "checked_by": ""},
        {"qid": "Q2", "query": "unknown topic", "expected_ids": "", "type": "no_match", "checked_by": ""},
    ])
    return path


def test_prepare_hides_types_ids_and_key_and_protects_outputs(tmp_path: Path) -> None:
    original = source(tmp_path)
    blind, mapping = tmp_path / "blind.csv", tmp_path / "private.csv"
    prepare(original, blind, mapping)
    content = blind.read_text()
    for secret in ("FTA-005", "expected_ids", "qid", "Q1", "Q2", "no_match", "exact"):
        assert secret not in content
    assert "wool" in content
    assert len(read_csv(mapping)) == 2
    with pytest.raises(ValueError, match="distinct paths"):
        prepare(original, blind, mapping)


def test_compare_requires_review_and_explicit_none(tmp_path: Path) -> None:
    original = source(tmp_path)
    blind, mapping = tmp_path / "blind.csv", tmp_path / "private.csv"
    prepare(original, blind, mapping)
    assert compare(original, blind, mapping) == (0, 0, 2)
    reviewed = read_csv(blind)
    for row in reviewed:
        row.update({"reviewed_ids": "FTA-005" if row["query"] == "wool" else "NONE",
                    "reviewer": "Reviewer A", "reviewed_on": "2026-10-25"})
    write_csv(blind, ["token", "query", "reviewed_ids", "reviewer", "reviewed_on"], reviewed)
    assert compare(original, blind, mapping) == (2, 0, 0)


def test_disagreement_never_rewrites_original(tmp_path: Path) -> None:
    original = source(tmp_path)
    before = original.read_bytes()
    blind, mapping = tmp_path / "blind.csv", tmp_path / "private.csv"
    prepare(original, blind, mapping)
    reviewed = read_csv(blind)
    for row in reviewed:
        row.update({"reviewed_ids": "FTA-010" if row["query"] == "wool" else "NONE",
                    "reviewer": "Reviewer A", "reviewed_on": "2026-10-25"})
    write_csv(blind, ["token", "query", "reviewed_ids", "reviewer", "reviewed_on"], reviewed)
    assert compare(original, blind, mapping) == (1, 1, 0)
    assert original.read_bytes() == before


def test_rejects_tampered_query(tmp_path: Path) -> None:
    original = source(tmp_path)
    blind, mapping = tmp_path / "blind.csv", tmp_path / "private.csv"
    prepare(original, blind, mapping)
    reviewed = read_csv(blind)
    reviewed[0]["query"] = "altered"
    write_csv(blind, ["token", "query", "reviewed_ids", "reviewer", "reviewed_on"], reviewed)
    with pytest.raises(ValueError, match="question text changed"):
        compare(original, blind, mapping)
