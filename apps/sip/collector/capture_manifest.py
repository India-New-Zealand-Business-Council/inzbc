"""Verify an exported news-agent capture before an authorised SIP-184 ingestion (#55).

This is an intentionally OFFLINE, read-only boundary. An article manifest is
not launch authority, a locked coverage window, a SIP-185 source determination,
or permission to write to the platform. No network, API writes or model calls.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

_ALLOWED_ARTICLE_FIELDS = frozenset({
    "title", "description", "url", "source", "published", "score",
    "nz_relevance_score", "sectors",
})
_ALLOWED_ROOT_FIELDS = frozenset({
    "schema_version", "kind", "production_run", "sip185_outcomes_confirmed",
    "fetch_started_utc", "fetch_finished_utc", "rolling_fetch_hours",
    "locked_sip184_window", "raw_article_count", "article_count",
    "coverage_state", "coverage_gaps", "source_fetch_health",
    "articles", "articles_sha256", "operator_notice",
})
_ALLOWED_OUTCOMES = frozenset({"ok", "no_recent", "partial", "empty", "error"})
_INCOMPLETE = frozenset({"partial", "empty", "error"})
_MAX_BYTES = 10 * 1024 * 1024
_MAX_ARTICLES = 5000


@dataclass(frozen=True)
class CaptureValidation:
    article_count: int
    fetch_source_count: int
    gaps: tuple[str, ...]
    articles_sha256: str
    fetch_started_utc: str
    fetch_finished_utc: str
    notice: str = (
        "Read-only check: no SIP-191 authority, locked 07:00 coverage, "
        "112-source SIP-185 outcome, approval, or candidate write was verified."
    )

    def report(self) -> dict:
        return {
            "validated_manifest": True,
            "production_run_verified": False,
            "sip185_source_outcomes_verified": False,
            "locked_coverage_window_verified": False,
            "article_count": self.article_count,
            "fetch_source_count": self.fetch_source_count,
            "fetch_coverage_gaps": list(self.gaps),
            "articles_sha256": self.articles_sha256,
            "fetch_started_utc": self.fetch_started_utc,
            "fetch_finished_utc": self.fetch_finished_utc,
            "notice": self.notice,
        }


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ) + "\n").encode("utf-8")


def _utc_time(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be an aware ISO8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a valid ISO8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _source_url(value: object) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError("each captured article needs a source URL")
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("article URL must be HTTP(S) with a hostname")
    if parts.username or parts.password or parts.hostname in ("localhost", "localhost.localdomain"):
        raise ValueError("article URL must not include credentials or localhost")
    try:
        address = ipaddress.ip_address(parts.hostname)
    except ValueError:
        if parts.hostname.endswith((".local", ".internal")):
            raise ValueError("article URL cannot refer to an internal host") from None
    else:
        if not address.is_global:
            raise ValueError("article URL cannot refer to a nonpublic IP address")


def _article(value: object) -> None:
    if not isinstance(value, dict):
        raise TypeError("each captured article must be an object")
    if set(value) - _ALLOWED_ARTICLE_FIELDS:
        raise ValueError("article has fields outside the approved clean_articles shape")
    if not isinstance(value.get("title"), str) or not value["title"].strip():
        raise ValueError("article title must be nonblank")
    if not isinstance(value.get("source"), str) or not value["source"].strip():
        raise ValueError("article source must be nonblank")
    _source_url(value.get("url"))
    for field in ("description", "published"):
        if field in value and not isinstance(value[field], str):
            raise TypeError(f"{field} must be a string")
    # The upstream agent.clean_articles() currently joins sector tags into a comma-
    # separated string. Accept that real producer shape plus legacy list fixtures;
    # do not coerce arbitrary untrusted types or change the checksummed payload.
    if "sectors" in value:
        sectors = value["sectors"]
        if not (
            isinstance(sectors, str)
            or (isinstance(sectors, list) and all(isinstance(tag, str) for tag in sectors))
        ):
            raise TypeError("sectors must be a string or list of strings")
    for field in ("score", "nz_relevance_score"):
        if field in value and (
            type(value[field]) not in (int, float)
            or not math.isfinite(float(value[field]))
        ):
            raise ValueError(f"{field} must be finite and numeric")


def validate_capture(snapshot: object) -> CaptureValidation:
    """Validate exporter evidence before exposing articles to the SIP capture path."""
    if not isinstance(snapshot, dict):
        raise TypeError("capture must be a JSON object")
    if set(snapshot) - _ALLOWED_ROOT_FIELDS:
        raise ValueError("capture contains unknown top-level fields")
    if snapshot.get("schema_version") != 1 or snapshot.get("kind") != "INZBC_SIP_REVIEW_CAPTURE":
        raise ValueError("unknown capture schema/kind")
    if (snapshot.get("production_run") is not False
            or snapshot.get("sip185_outcomes_confirmed") is not False
            or snapshot.get("locked_sip184_window") is not False):
        raise ValueError("capture may not assert launch, SIP-185, or locked-window authority")
    started = _utc_time(snapshot.get("fetch_started_utc"), "fetch_started_utc")
    finished = _utc_time(snapshot.get("fetch_finished_utc"), "fetch_finished_utc")
    if finished < started:
        raise ValueError("fetch finished before it began")
    hours = snapshot.get("rolling_fetch_hours")
    if type(hours) is not int or not 1 <= hours <= 168:
        raise ValueError("rolling_fetch_hours must be an integer from 1 to 168")
    articles = snapshot.get("articles")
    if not isinstance(articles, list) or len(articles) > _MAX_ARTICLES:
        raise TypeError("articles must be a bounded list")
    for item in articles:
        _article(item)
    raw_count = snapshot.get("raw_article_count")
    if (type(raw_count) is not int or raw_count < len(articles)
            or type(snapshot.get("article_count")) is not int
            or snapshot["article_count"] != len(articles)):
        raise ValueError("article counts are inconsistent")
    actual_hash = hashlib.sha256(_canonical_bytes(articles)).hexdigest()
    if snapshot.get("articles_sha256") != actual_hash:
        raise ValueError("articles checksum mismatch")
    health = snapshot.get("source_fetch_health")
    if not isinstance(health, dict) or not health:
        raise ValueError("capture must have observed per-source fetch status")
    for name, row in health.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(row, dict):
            raise ValueError("invalid fetch status")
        if set(row) != {"fetch_outcome", "queries_failed", "queries_total"}:
            raise ValueError("invalid fetch-status fields")
        if row["fetch_outcome"] not in _ALLOWED_OUTCOMES:
            raise ValueError("invalid fetch outcome")
        failed = row["queries_failed"]
        total = row["queries_total"]
        if type(failed) is not int or type(total) is not int or failed < 0 or total < 0:
            raise ValueError("query counters must be nonnegative integers")
        if failed > total:
            raise ValueError("failed queries exceed total")
        if row["fetch_outcome"] in {"ok", "no_recent"} and failed:
            raise ValueError("healthy fetch outcome cannot report failed queries")
        if row["fetch_outcome"] == "partial" and (total == 0 or failed == 0 or failed == total):
            raise ValueError("partial fetch must have both successful and failed queries")
    gaps = tuple(sorted(
        name for name, row in health.items()
        if row["fetch_outcome"] in _INCOMPLETE
    ))
    if snapshot.get("coverage_gaps") != list(gaps):
        raise ValueError("coverage gaps do not match source-health evidence")
    if snapshot.get("coverage_state") != ("incomplete" if gaps else "observed"):
        raise ValueError("coverage state does not match the observed gaps")
    return CaptureValidation(
        article_count=len(articles),
        fetch_source_count=len(health),
        gaps=gaps,
        articles_sha256=actual_hash,
        fetch_started_utc=started.isoformat(),
        fetch_finished_utc=finished.isoformat(),
    )


def validate_file(path: Path) -> CaptureValidation:
    if path.stat().st_size > _MAX_BYTES:
        raise ValueError("capture exceeds 10 MiB safety limit")
    with path.open(encoding="utf-8") as handle:
        return validate_capture(json.load(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_file(args.capture).report()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
