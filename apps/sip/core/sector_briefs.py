"""On-demand Sector Opportunity Briefs built on the existing SIP scorer and source register (#194).

Reuses `apps.sip.core.scoring.score_batch` and `apps.sip.collector.source_register.ALL_SOURCES`
rather than introducing a parallel pipeline. Every brief produced here is strictly an advisory
draft (`advisory_only=True`, `requires_human_review=True`, `approved=False`) and can never
escalate unverified items or authorise distribution.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.sip.collector.source_register import ALL_SOURCES, SourceRegisterEntry
from apps.sip.core.scoring import (
    MAX_BATCH_CANDIDATES,
    ScoringCandidate,
    ScoringRecommendation,
    score_batch,
)
from services.api.model_gateway import ModelGateway

PRIORITY_CORRIDORS: tuple[dict[str, str], ...] = (
    {
        "slug": "dairy-and-food",
        "name": "Dairy, Food & Primary Exports",
        "focus": "Tariff schedules, sanitary/phytosanitary access, cold-chain and retail partnerships.",
    },
    {
        "slug": "horticulture-and-wine",
        "name": "Horticulture, Kiwifruit & Wine",
        "focus": "Phytosanitary protocols, seasonal demand, port clearance and tariff staging.",
    },
    {
        "slug": "agritech-and-forestry",
        "name": "AgriTech, Forestry & Wool",
        "focus": "Precision agriculture, timber standards, wool processing and joint R&D.",
    },
    {
        "slug": "education-and-skills",
        "name": "International Education & Skills Mobility",
        "focus": "Visa pathways, institutional partnerships, joint degrees and qualification recognition.",
    },
    {
        "slug": "tech-and-digital",
        "name": "Technology, SaaS & Digital Services",
        "focus": "Cross-border IT delivery, fintech, AI governance and digital trade facilitation.",
    },
    {
        "slug": "clean-energy-and-infra",
        "name": "Clean Energy, Climate & Infrastructure",
        "focus": "Geothermal, solar, grid modernisation, green hydrogen and sustainable transport.",
    },
    {
        "slug": "tourism-and-aviation",
        "name": "Tourism, Aviation & Connectivity",
        "focus": "Direct air links, visitor visas, business delegations and hospitality investment.",
    },
)

_CORRIDOR_BY_SLUG: dict[str, dict[str, str]] = {c["slug"]: c for c in PRIORITY_CORRIDORS}
_SOURCE_BY_ID: dict[str, SourceRegisterEntry] = {s.source_id: s for s in ALL_SOURCES}

_SIGNAL_RANK: dict[str, int] = {
    "Critical": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
    "Noise": 0,
}


@dataclass(frozen=True)
class SectorCandidateInput:
    """One article candidate submitted for an on-demand sector opportunity brief."""

    id: str
    source_id: str
    headline: str
    published: str
    url: str
    summary: str | None = None


@dataclass(frozen=True)
class SectorOpportunityItem:
    """One scored opportunity item inside an advisory sector brief."""

    candidate_id: str
    source_id: str
    source_name: str
    source_layer: int
    headline: str
    url: str
    published: str
    nz_relevance: int
    india_relevance: int
    member_relevance: int
    signal: str
    confidence: str
    reason: str
    requires_verification: bool


@dataclass(frozen=True)
class SectorOpportunityBrief:
    """Advisory sector opportunity brief. Never approved or distributable without human review."""

    corridor_slug: str
    corridor_name: str
    corridor_focus: str
    items: tuple[SectorOpportunityItem, ...]
    evaluated_count: int
    included_count: int
    advisory_only: bool = True
    requires_human_review: bool = True
    approved: bool = False
    distribution_permitted: bool = False
    notice: str = (
        "Advisory draft generated via the SIP-050 scorer. Human verification and approval are "
        "required before any external circulation; High and Critical signals remain unverified."
    )


def list_priority_corridors() -> list[dict[str, object]]:
    """Return the Chair's priority corridors alongside the SIP-185 source register totals."""
    total_sources = len(ALL_SOURCES)
    mandatory_count = sum(1 for s in ALL_SOURCES if s.mandatory)
    return [
        {
            **corridor,
            "register_source_count": total_sources,
            "mandatory_source_count": mandatory_count,
        }
        for corridor in PRIORITY_CORRIDORS
    ]


def build_sector_opportunity_brief(
    gateway: ModelGateway,
    *,
    corridor_slug: str,
    candidates: list[SectorCandidateInput],
    min_signal: str = "Medium",
) -> SectorOpportunityBrief:
    """Generate an on-demand advisory sector brief using the existing SIP batch scorer.

    Fails closed on unknown corridors, unregistered SIP-185 source IDs, invalid signal
    thresholds, or batches exceeding `MAX_BATCH_CANDIDATES`.
    """
    corridor = _CORRIDOR_BY_SLUG.get(corridor_slug)
    if corridor is None:
        raise ValueError(f"unknown priority corridor {corridor_slug!r}")
    if min_signal not in _SIGNAL_RANK:
        raise ValueError(f"invalid min_signal {min_signal!r}")
    if len(candidates) > MAX_BATCH_CANDIDATES:
        raise ValueError(
            f"batch contains {len(candidates)} candidates; maximum is {MAX_BATCH_CANDIDATES}"
        )

    scoring_inputs: list[ScoringCandidate] = []
    source_entries: dict[str, SourceRegisterEntry] = {}
    for item in candidates:
        source_entry = _SOURCE_BY_ID.get(item.source_id)
        if source_entry is None:
            raise ValueError(
                f"candidate {item.id!r} references unregistered SIP-185 source {item.source_id!r}"
            )
        source_entries[item.id] = source_entry
        scoring_inputs.append(
            ScoringCandidate(
                id=item.id,
                headline=item.headline,
                source=source_entry.name,
                published=item.published,
                url=item.url,
                summary=item.summary or "",
            )
        )

    recommendations: dict[str, ScoringRecommendation] = score_batch(gateway, scoring_inputs)
    threshold = _SIGNAL_RANK[min_signal]

    ranked_items: list[SectorOpportunityItem] = []
    for item in candidates:
        rec = recommendations[item.id]
        if _SIGNAL_RANK[rec.signal.value] < threshold:
            continue
        source_entry = source_entries[item.id]
        ranked_items.append(
            SectorOpportunityItem(
                candidate_id=item.id,
                source_id=source_entry.source_id,
                source_name=source_entry.name,
                source_layer=source_entry.layer,
                headline=item.headline,
                url=item.url,
                published=item.published,
                nz_relevance=rec.nz_relevance,
                india_relevance=rec.india_relevance,
                member_relevance=rec.member_relevance,
                signal=rec.signal.value,
                confidence=rec.confidence.value,
                reason=rec.reason,
                # High and Critical items always require human verification before inclusion.
                requires_verification=rec.signal.value in {"High", "Critical"},
            )
        )

    ranked_items.sort(
        key=lambda x: (
            _SIGNAL_RANK[x.signal],
            x.member_relevance,
            x.nz_relevance + x.india_relevance,
        ),
        reverse=True,
    )

    return SectorOpportunityBrief(
        corridor_slug=corridor["slug"],
        corridor_name=corridor["name"],
        corridor_focus=corridor["focus"],
        items=tuple(ranked_items),
        evaluated_count=len(candidates),
        included_count=len(ranked_items),
    )
