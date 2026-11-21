"""Unit tests for Sector Opportunity Briefs (#194)."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from apps.sip.collector.source_register import ALL_SOURCES
from apps.sip.core.sector_briefs import (
    SectorCandidateInput,
    build_sector_opportunity_brief,
    list_priority_corridors,
)


@dataclass
class _StubCompletion:
    text: str


class _StubGateway:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def complete(self, prompt, *, source):
        _ = (prompt, source)
        payload = self._responses[self.calls]
        self.calls += 1
        return _StubCompletion(text=json.dumps(payload))


def _first_source_id() -> str:
    return ALL_SOURCES[0].source_id


def test_list_priority_corridors_exposes_register_totals() -> None:
    corridors = list_priority_corridors()
    assert len(corridors) >= 5
    assert corridors[0]["register_source_count"] == len(ALL_SOURCES)
    assert corridors[0]["mandatory_source_count"] == 112


def test_build_sector_brief_ranks_filters_and_marks_advisory() -> None:
    sid = _first_source_id()
    gateway = _StubGateway(
        [
            {
                "nz_relevance": 2,
                "india_relevance": 2,
                "member_relevance": 1,
                "signal": "Low",
                "confidence": "Medium",
                "reason": "Minor local update",
            },
            {
                "nz_relevance": 5,
                "india_relevance": 5,
                "member_relevance": 5,
                "signal": "High",
                "confidence": "High",
                "reason": "Direct dairy cold-chain tariff reduction schedule",
            },
            {
                "nz_relevance": 4,
                "india_relevance": 3,
                "member_relevance": 4,
                "signal": "Medium",
                "confidence": "Medium",
                "reason": "Retail distribution partnership inquiry",
            },
        ]
    )
    candidates = [
        SectorCandidateInput(
            id="c1",
            source_id=sid,
            headline="Minor local note",
            published="2026-11-20T01:00:00Z",
            url="https://example.org/c1",
        ),
        SectorCandidateInput(
            id="c2",
            source_id=sid,
            headline="NZ-India cold-chain tariff milestone",
            published="2026-11-20T02:00:00Z",
            url="https://example.org/c2",
        ),
        SectorCandidateInput(
            id="c3",
            source_id=sid,
            headline="Indian grocery chain seeks NZ dairy suppliers",
            published="2026-11-20T03:00:00Z",
            url="https://example.org/c3",
        ),
    ]

    brief = build_sector_opportunity_brief(
        gateway,  # type: ignore[arg-type]
        corridor_slug="dairy-and-food",
        candidates=candidates,
        min_signal="Medium",
    )

    assert brief.advisory_only is True
    assert brief.requires_human_review is True
    assert brief.approved is False
    assert brief.distribution_permitted is False
    assert brief.evaluated_count == 3
    assert brief.included_count == 2
    assert [item.candidate_id for item in brief.items] == ["c2", "c3"]
    assert brief.items[0].requires_verification is True
    assert brief.items[1].requires_verification is False


def test_build_sector_brief_rejects_unknown_corridor() -> None:
    gateway = _StubGateway([])
    with pytest.raises(ValueError, match="unknown priority corridor"):
        build_sector_opportunity_brief(
            gateway,  # type: ignore[arg-type]
            corridor_slug="not-a-corridor",
            candidates=[],
        )


def test_build_sector_brief_rejects_unregistered_source_id() -> None:
    gateway = _StubGateway([])
    with pytest.raises(ValueError, match="unregistered SIP-185 source"):
        build_sector_opportunity_brief(
            gateway,  # type: ignore[arg-type]
            corridor_slug="dairy-and-food",
            candidates=[
                SectorCandidateInput(
                    id="c1",
                    source_id="UNKNOWN-999",
                    headline="Unregistered source item",
                    published="2026-11-20T01:00:00Z",
                    url="https://example.org/x",
                )
            ],
        )
