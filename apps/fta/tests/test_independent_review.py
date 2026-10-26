"""Regression tests for blinded, independent answer-label review."""
import csv
from pathlib import Path

import pytest

from apps.fta.eval.independent_review import compare, prepare


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def source(tmp_path: Path) -> Path:
    path = tmp_path / "original.csv"
    write_csv(path, ["qid", "query", "expected_ids", "type", "checked_by"], [
        {"qid": "Q1", "query": "wool", "expected_ids": "FTA-005", "type": "exact", "checked_by": ""},
        {"qid": "Q2", "query": "unknown topic", "expected_ids": "", "type": "no_match", "checked_by": ""},
    ])
    return path


def test_prepare_hides_original_expected_ids(tmp_path: Path) -> None:
    original = source(tmp_path)
    blind = tmp_path / "blind.csv"
    prepare(original, blind)
    content = blind.read_text()
    assert "FTA-005" not in content
    assert "expected_ids" not in content
    assert "wool" in content
    with pytest.raises(ValueError, match="new file"):
        prepare(original, blind)


def test_compare_requires_real_review_and_explicit_none(tmp_path: Path) -> None:
    original = source(tmp_path)
    blind = tmp_path / "blind.csv"
    prepare(original, blind)
    assert compare(original, blind) == (0, 0, 2)
    write_csv(blind, ["qid", "query", "type", "reviewed_ids", "reviewer", "reviewed_on"], [
        {"qid": "Q1", "query": "wool", "type": "exact", "reviewed_ids": "FTA-005",
         "reviewer": "Reviewer A", "reviewed_on": "2026-10-26"},
        {"qid": "Q2", "query": "unknown topic", "type": "no_match", "reviewed_ids": "NONE",
         "reviewer": "Reviewer A", "reviewed_on": "2026-10-26"},
    ])
    assert compare(original, blind) == (2, 0, 0)


def test_compare_reports_disagreement_without_changing_source(tmp_path: Path) -> None:
    original = source(tmp_path)
    initial = original.read_bytes()
    blind = tmp_path / "blind.csv"
    write_csv(blind, ["qid", "query", "type", "reviewed_ids", "reviewer", "reviewed_on"], [
        {"qid": "Q1", "query": "wool", "type": "exact", "reviewed_ids": "FTA-010",
         "reviewer": "Reviewer A", "reviewed_on": "2026-10-26"},
        {"qid": "Q2", "query": "unknown topic", "type": "no_match", "reviewed_ids": "NONE",
         "reviewer": "Reviewer A", "reviewed_on": "2026-10-26"},
    ])
    assert compare(original, blind) == (1, 1, 0)
    assert original.read_bytes() == initial


def test_rejects_question_changes(tmp_path: Path) -> None:
    original = source(tmp_path)
    blind = tmp_path / "blind.csv"
    write_csv(blind, ["qid", "query", "type", "reviewed_ids", "reviewer", "reviewed_on"], [
        {"qid": "Q1", "query": "altered", "type": "exact", "reviewed_ids": "",
         "reviewer": "", "reviewed_on": ""},
        {"qid": "Q2", "query": "unknown topic", "type": "no_match", "reviewed_ids": "",
         "reviewer": "", "reviewed_on": ""},
    ])
    with pytest.raises(ValueError, match="query/type changed"):
        compare(original, blind)
