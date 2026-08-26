"""Generates docs/sip-collector-pipeline-evidence.md: a measured run of the collector pipeline
logic proving the claims in #337 rather than asserting them.

Runs entirely offline against synthetic, obviously-labelled articles (no live backend, no real
SIP-185 data written) — this measures `dedupe.py`, `ingest.py` and `source_register.py` behaviour
directly, the same way `apps/sip/collector/tests/` does, just reported instead of asserted. Rerun
after any change to those three modules:

    python -m scripts.sip_collector_pipeline_evidence

Not a SIP-184 production run and not a substitute for `run_dry_run.py` (which exercises the real
HTTP client against a live backend). This script only proves the three specific things #337 asked
for: dedupe actually catching duplicates with counts, per-item isolation on a malformed article,
and the mandatory-source gate reporting (not raising on) uncovered sources.
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.sip.collector.dedupe import find_duplicate_of, normalize_url  # noqa: E402
from apps.sip.collector.ingest import ingest_articles  # noqa: E402
from apps.sip.collector.source_register import (  # noqa: E402
    MANDATORY_SOURCES,
    missing_mandatory_outcomes,
)

_OUT = (
    Path(__file__).resolve().parents[1] / "docs" / "sip-collector-pipeline-evidence.md"
)
_RUN_ID = "00000000-0000-0000-0000-000000000000"

_TAG = "SYNTHETIC TEST DATA"


class _FakeClient:
    """Same fake used by apps/sip/collector/tests/test_ingest.py: records what it was asked to
    create, no network, no live SIP-185 write. Kept in sync deliberately rather than imported,
    same as the test file does, so this script has no import-time dependency on the test suite.
    """

    def __init__(self) -> None:
        self.created_payloads: list[dict] = []

    def create_candidate(self, candidate) -> dict:
        payload = candidate.model_dump(mode="json", exclude_none=True)
        self.created_payloads.append(payload)
        return {"id": f"created-{len(self.created_payloads)}", **payload}


def _article(*, url: str, **overrides: object) -> dict:
    base = {
        "title": f"{_TAG} - India, NZ discuss FTA next steps",
        "description": f"{_TAG} - officials met to progress trade talks.",
        "url": url,
        "source": "RNZ Business",
        "published": "2026-08-20T19:32:00+00:00",
        "score": 34,
        "nz_relevance_score": 15,
        "sectors": "Trade and FTA",
    }
    base.update(overrides)
    return base


# Already-captured candidates from an earlier (simulated) run, against which new articles are
# checked for duplicates - the cross-run case dedupe.py exists for (see its module docstring).
_ALREADY_CAPTURED = [
    {
        "id": "cand-001",
        "url": "https://example.invalid/evidence/fta-next-steps",
        "headline": f"{_TAG} - India, NZ discuss FTA next steps",
    },
    {
        "id": "cand-002",
        "url": "https://example.invalid/evidence/dairy-tariff-review",
        "headline": f"{_TAG} - Dairy exporters watch India tariff review",
    },
]

# The incoming batch: a mix of genuinely-new articles, a url-duplicate (trailing slash + case
# difference from cand-001), a headline-duplicate with a different url from cand-002, and one
# malformed item (title missing entirely - Candidate.headline is required).
_INCOMING_BATCH: list[object] = [
    _article(
        title=f"{_TAG} - Kiwifruit exporters welcome new India quota",
        url="https://example.invalid/evidence/kiwifruit-quota",
    ),
    _article(
        title=f"{_TAG} - FTA next steps (wire copy)",
        url="HTTPS://EXAMPLE.INVALID/evidence/fta-next-steps/",  # url-dupe of cand-001
    ),
    _article(
        title=f"{_TAG} -   Dairy exporters watch India   tariff review",  # whitespace/case-dupe of cand-002 by headline
        url="https://example.invalid/evidence/dairy-tariff-review-syndicated",
    ),
    _article(
        title=f"{_TAG} - Manuka honey exporters see cut tariff take effect",
        url="https://example.invalid/evidence/manuka-honey-tariff",
    ),
    {  # malformed: no "title" key at all
        "description": f"{_TAG} - malformed fixture item, no title field.",
        "url": "https://example.invalid/evidence/malformed-item",
        "source": "GDELT",
        "published": "2026-08-20T20:00:00+00:00",
        "score": 5,
        "nz_relevance_score": 2,
        "sectors": "",
    },
    _article(
        title=f"{_TAG} - Wine exporters ask about MFN clause",
        url="https://example.invalid/evidence/wine-mfn-clause",
    ),
]


def _dedupe_section() -> tuple[list[str], int]:
    lines = ["## 1. Cross-run duplicate detection (`dedupe.py`)", ""]
    duplicate_count = 0
    lines.append("| Incoming article | Matched against | Matched by |")
    lines.append("| --- | --- | --- |")
    for article in _INCOMING_BATCH:
        if not isinstance(article, dict) or "title" not in article:
            continue  # the malformed item has no dedupe-relevant fields; covered in section 2
        duplicate_id = find_duplicate_of(article, _ALREADY_CAPTURED)
        if duplicate_id:
            duplicate_count += 1
            match = next(c for c in _ALREADY_CAPTURED if c["id"] == duplicate_id)
            matched_by = (
                "url"
                if normalize_url(article.get("url")) == normalize_url(match["url"])
                else "headline"
            )
            lines.append(f"| {article['title']!r} | `{duplicate_id}` | {matched_by} |")
        else:
            lines.append(f"| {article['title']!r} | — | not a duplicate |")
    lines.append("")
    lines.append(
        f"**{duplicate_count} of {sum(1 for a in _INCOMING_BATCH if isinstance(a, dict) and 'title' in a)} "
        f"well-formed incoming articles matched an already-captured candidate** — one by "
        f"normalized url (case + trailing-slash difference), one by normalized headline "
        f"(whitespace + wording difference, different url). Neither would have matched on exact "
        f"string equality, which is what `find_duplicate_of` normalizes for."
    )
    lines.append("")
    return lines, duplicate_count


def _ingest_section() -> list[str]:
    client = _FakeClient()
    result = ingest_articles(client, _RUN_ID, _INCOMING_BATCH)

    lines = ["## 2. Per-item isolation on a malformed article (`ingest.py`)", ""]
    lines.append(
        "Ran the full 6-item batch above (including the 1 malformed item with no `title`) "
        "through `ingest_articles` in one call."
    )
    lines.append("")
    lines.append(f"- Candidates created: **{len(result.created)}**")
    lines.append(f"- Items failed: **{len(result.failed)}**")
    lines.append("")
    if result.failed:
        lines.append("Failures (isolated — did not stop the other items in the batch):")
        lines.append("")
        for failure in result.failed:
            lines.append(f"- `{asdict(failure)}`")
    lines.append("")
    created_titles = [p["headline"] for p in client.created_payloads]
    lines.append(
        "Created despite the malformed item sitting between them in the batch:"
    )
    lines.append("")
    for title in created_titles:
        lines.append(f"- {title!r}")
    lines.append("")
    return lines


def _mandatory_source_gate_section() -> list[str]:
    lines = [
        "## 3. Mandatory-source coverage gate reports rather than raises (`source_register.py`)",
        "",
    ]
    lines.append(
        f"`MANDATORY_SOURCES` (SIP-185 v1.0 register): **{len(MANDATORY_SOURCES)}** sources."
    )
    lines.append("")
    no_outcomes_recorded = missing_mandatory_outcomes(set())
    lines.append(
        f"With zero source outcomes recorded this run: `missing_mandatory_outcomes(set())` "
        f"returns **{len(no_outcomes_recorded)}** ids — every mandatory source, as expected — and "
        f"returns normally rather than raising. It is a report function, not a gate that blocks "
        f"execution; the caller (SIP-184 step 4/11) is the one that must treat a non-empty result "
        f"as a Critical stop before submitting a run for QA."
    )
    lines.append("")
    partial = {s.source_id for s in MANDATORY_SOURCES[:3]}
    still_missing = missing_mandatory_outcomes(partial)
    lines.append(
        f"With outcomes recorded for the first {len(partial)} mandatory sources "
        f"(`{sorted(partial)}`): **{len(still_missing)}** remain missing — confirms the function "
        f"reports exactly the *uncovered* set, not a fixed total."
    )
    lines.append("")
    lines.append(f"First 5 still-missing ids: `{still_missing[:5]}`")
    lines.append("")
    return lines


def build_report() -> str:
    lines = ["# SIP collector pipeline evidence", ""]
    lines.append(
        f"Generated by `scripts/sip_collector_pipeline_evidence.py` — a measured, offline run of "
        f"`dedupe.py`, `ingest.py` and `source_register.py` against synthetic fixture data (all "
        f"articles below are tagged `{_TAG}`; none is a real news item, real trade fact, or real "
        f"SIP-185 write). Rerun the script to reproduce these counts; do not hand-edit this file."
    )
    lines.append("")
    lines.append(
        "**What this does not prove:** this does not exercise the live `SipPipelineClient` HTTP "
        "path, the database, or a real SIP-184 authorised run — see `run_dry_run.py` for that. It "
        "proves the pure dedupe/ingest/gate logic does what its docstrings claim, with counts from "
        "an actual run of that code, not from reading it."
    )
    lines.append("")

    dedupe_lines, _ = _dedupe_section()
    lines += dedupe_lines
    lines += _ingest_section()
    lines += _mandatory_source_gate_section()
    return "\n".join(lines)


def main() -> int:
    report = build_report()
    _OUT.write_text(report, encoding="utf-8")
    print(f"wrote {_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
