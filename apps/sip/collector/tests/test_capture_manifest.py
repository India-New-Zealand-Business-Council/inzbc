"""Cross-repository manifest contract tests; all inputs are synthetic."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from apps.sip.collector import capture_manifest as m


@pytest.fixture
def manifest() -> dict:
    articles = [{
        "title": "Test New Zealand India trade",
        "url": "https://example.org/trade",
        "source": "RNZ Business",
        "published": "2026-10-26T01:00:00+00:00",
        "description": "synthetic example",
        "score": 5,
        "nz_relevance_score": 10,
        "sectors": "Trade and FTA",
    }]
    return {
        "schema_version": 1,
        "kind": "INZBC_SIP_REVIEW_CAPTURE",
        "production_run": False,
        "sip185_outcomes_confirmed": False,
        "locked_sip184_window": False,
        "fetch_started_utc": "2026-10-26T02:00:00+00:00",
        "fetch_finished_utc": "2026-10-26T02:05:00+00:00",
        "rolling_fetch_hours": 24,
        "raw_article_count": 3,
        "article_count": 1,
        "coverage_state": "incomplete",
        "coverage_gaps": ["GDELT"],
        "source_fetch_health": {
            "GDELT": {"fetch_outcome": "partial", "queries_failed": 17, "queries_total": 18},
            "RNZ Business": {"fetch_outcome": "ok", "queries_failed": 0, "queries_total": 0},
        },
        "articles": articles,
        "articles_sha256": hashlib.sha256(m._canonical_bytes(articles)).hexdigest(),
        "operator_notice": "Synthetic review-only test fixture",
    }


def test_valid_manifest_never_claims_approval(manifest: dict) -> None:
    result = m.validate_capture(manifest)
    assert result.article_count == 1
    assert result.fetch_source_count == 2
    assert result.gaps == ("GDELT",)
    assert result.report()["production_run_verified"] is False
    assert result.report()["sip185_source_outcomes_verified"] is False
    assert result.report()["locked_coverage_window_verified"] is False


def test_legacy_list_sectors_remain_supported(manifest: dict) -> None:
    # The live news-agent emits a string, but earlier synthetic captures used a list.
    article = manifest["articles"][0]
    article["sectors"] = ["Trade and FTA"]
    manifest["articles_sha256"] = hashlib.sha256(
        m._canonical_bytes(manifest["articles"])
    ).hexdigest()
    assert m.validate_capture(manifest).article_count == 1



def test_tampering_with_string_sector_invalidates_capture_checksum(manifest: dict) -> None:
    # A real news-agent packet uses a string rather than a list of sector tags.
    # Its checksum must bind that exact string, not only the title or URL.
    original_hash = manifest["articles_sha256"]
    manifest["articles"][0]["sectors"] = "Trade and FTA, Agriculture"
    assert manifest["articles_sha256"] == original_hash

    with pytest.raises(ValueError, match="articles checksum mismatch"):
        m.validate_capture(manifest)


@pytest.mark.parametrize("mutate,match", [
    (lambda s: s.update(production_run=True), "may not assert"),
    (lambda s: s.update(sip185_outcomes_confirmed=True), "may not assert"),
    (lambda s: s.update(locked_sip184_window=True), "may not assert"),
    (lambda s: s.update(articles_sha256="0"*64), "checksum"),
    (lambda s: s["articles"][0].update(title="Tampered"), "checksum"),
    (lambda s: s["articles"][0].update(url="file:///etc/passwd"), "HTTP"),
    (lambda s: s["articles"][0].update(url="http://127.0.0.1/admin"), "nonpublic"),
    (lambda s: s["articles"][0].update(password="secret"), "outside"),
    (lambda s: s["articles"][0].update(sectors=42), "sectors must"),
    (lambda s: s["articles"][0].update(sectors=["Trade", 42]), "sectors must"),
    (lambda s: s["source_fetch_health"]["GDELT"].update(fetch_outcome="Included"), "fetch outcome"),
    (lambda s: s["source_fetch_health"]["GDELT"].update(queries_failed=19), "exceed"),
    (lambda s: s["source_fetch_health"]["GDELT"].update(queries_failed=1, queries_total=0), "exceed"),
    (lambda s: s["source_fetch_health"]["RNZ Business"].update(queries_failed=1, queries_total=2), "healthy"),
    (lambda s: s["source_fetch_health"]["GDELT"].update(queries_failed=0), "partial fetch"),
    (lambda s: s["source_fetch_health"]["GDELT"].update(queries_failed=18), "partial fetch"),
    (lambda s: s.update(coverage_state="observed"), "coverage state"),
    (lambda s: s.update(coverage_gaps=[]), "coverage gaps"),
    (lambda s: s.update(rolling_fetch_hours=True), "rolling_fetch_hours"),
    (lambda s: s.update(article_count=3), "article counts"),
    (lambda s: s.update(fetch_started_utc="2026-10-26"), "timezone-aware"),
    (lambda s: s.update(fetch_finished_utc="2026-10-25T01:00:00Z"), "before"),
    (lambda s: s.update(fake_authorization="approved"), "unknown top-level"),
])
def test_invalid_manifest_fails_closed(manifest: dict, mutate, match: str) -> None:
    tampered = deepcopy(manifest)
    mutate(tampered)
    with pytest.raises((ValueError, TypeError), match=match):
        m.validate_capture(tampered)


def test_file_and_cli_report_are_read_only(
    manifest: dict, tmp_path: Path, capsys
) -> None:
    artifact = tmp_path / "capture.json"
    artifact.write_text(json.dumps(manifest), encoding="utf-8")
    assert m.main(["--capture", str(artifact)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["article_count"] == 1
    assert printed["production_run_verified"] is False
    assert json.loads(artifact.read_text()) == manifest


def test_oversized_file_rejected_before_json_load(tmp_path: Path) -> None:
    path = tmp_path / "too-large.json"
    path.write_bytes(b"x" * (10 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="10 MiB"):
        m.validate_file(path)
