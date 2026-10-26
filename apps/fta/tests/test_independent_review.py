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
    ] + [
        {"qid": f"Q{i}", "query": f"query {i}", "expected_ids": f"FTA-{i:03d}",
         "type": "exact", "checked_by": ""} for i in range(3, 11)
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
    assert len(read_csv(mapping)) == 10
    assert all("source_sha256" in row for row in read_csv(mapping))
    with pytest.raises(ValueError, match="distinct paths"):
        prepare(original, blind, mapping)


def test_compare_requires_review_and_explicit_none(tmp_path: Path) -> None:
    original = source(tmp_path)
    blind, mapping = tmp_path / "blind.csv", tmp_path / "private.csv"
    prepare(original, blind, mapping)
    assert compare(original, blind, mapping) == (0, 0, 10)
    reviewed = read_csv(blind)
    for row in reviewed:
        row.update({"reviewed_ids": ("FTA-005" if row["query"] == "wool" else "NONE" if row["query"] == "unknown topic" else f"FTA-{int(row['query'].split()[1]):03d}"),
                    "reviewer": "Reviewer A", "reviewed_on": "2026-10-25",
                    "evidence": "Verified corpus citation", "uncertainty": "none"})
    write_csv(blind, ["token", "query", "reviewed_ids", "reviewer", "reviewed_on", "evidence", "uncertainty"], reviewed)
    assert compare(original, blind, mapping) == (10, 0, 0)


def test_disagreement_never_rewrites_original(tmp_path: Path) -> None:
    original = source(tmp_path)
    before = original.read_bytes()
    blind, mapping = tmp_path / "blind.csv", tmp_path / "private.csv"
    prepare(original, blind, mapping)
    reviewed = read_csv(blind)
    for row in reviewed:
        row.update({"reviewed_ids": ("FTA-010" if row["query"] == "wool" else "NONE" if row["query"] == "unknown topic" else f"FTA-{int(row['query'].split()[1]):03d}"),
                    "reviewer": "Reviewer A", "reviewed_on": "2026-10-25",
                    "evidence": "Verified corpus citation", "uncertainty": "none"})
    write_csv(blind, ["token", "query", "reviewed_ids", "reviewer", "reviewed_on", "evidence", "uncertainty"], reviewed)
    assert compare(original, blind, mapping) == (9, 1, 0)
    assert original.read_bytes() == before


def test_rejects_tampered_query(tmp_path: Path) -> None:
    original = source(tmp_path)
    blind, mapping = tmp_path / "blind.csv", tmp_path / "private.csv"
    prepare(original, blind, mapping)
    reviewed = read_csv(blind)
    reviewed[0]["query"] = "altered"
    write_csv(blind, ["token", "query", "reviewed_ids", "reviewer", "reviewed_on", "evidence", "uncertainty"], reviewed)
    with pytest.raises(ValueError, match="question text changed"):
        compare(original, blind, mapping)


def test_changed_source_label_fails_closed(tmp_path: Path) -> None:
    original = source(tmp_path)
    blind, mapping = tmp_path / "blind.csv", tmp_path / "private.csv"
    prepare(original, blind, mapping)
    changed = read_csv(original)
    changed[0]["expected_ids"] = "FTA-999"
    write_csv(original, ["qid", "query", "expected_ids", "type", "checked_by"], changed)
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        compare(original, blind, mapping)


def test_mapping_is_private_on_posix(tmp_path: Path) -> None:
    import os

    original = source(tmp_path)
    blind, mapping = tmp_path / "blind.csv", tmp_path / "private.csv"
    prepare(original, blind, mapping)
    if os.name == "posix":
        assert mapping.stat().st_mode & 0o077 == 0


def test_requires_coordinator_sample_of_ten(tmp_path: Path) -> None:
    original = source(tmp_path)
    rows = read_csv(original)[:-1]
    write_csv(original, ["qid", "query", "expected_ids", "type", "checked_by"], rows)
    with pytest.raises(ValueError, match="ten-question"):
        prepare(original, tmp_path / "blind.csv", tmp_path / "private.csv")


def test_failed_review_create_cleans_mapping_without_touching_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.fta.eval import independent_review

    original = source(tmp_path)
    blind, mapping = tmp_path / "blind.csv", tmp_path / "private.csv"
    real_write = independent_review.write_rows

    def simulate_racing_existing_file(path: Path, fields: tuple[str, ...],
                                      rows: list[dict[str, str]]) -> None:
        if path == blind:
            blind.write_text("Existing review file must survive", encoding="utf-8")
        real_write(path, fields, rows)

    monkeypatch.setattr(independent_review, "write_rows", simulate_racing_existing_file)
    with pytest.raises(FileExistsError):
        prepare(original, blind, mapping)
    assert not mapping.exists()
    assert blind.read_text(encoding="utf-8") == "Existing review file must survive"
