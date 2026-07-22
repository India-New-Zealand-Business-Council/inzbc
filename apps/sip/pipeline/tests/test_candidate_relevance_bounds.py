"""Checks that Candidate's 0..5 relevance fields actually enforce that range.

ADR-0001 commits to "Pydantic enforces validation at trust boundaries" - these fields carried a
"0..5 scores" comment but no Field constraint, so any int passed validation silently.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.sip.pipeline.models import Candidate

RUN_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.parametrize("field", ["nz_relevance", "india_relevance", "member_relevance"])
@pytest.mark.parametrize("value", [0, 3, 5])
def test_relevance_accepts_values_in_range(field: str, value: int) -> None:
    candidate = Candidate(run_id=RUN_ID, headline="h", **{field: value})
    assert getattr(candidate, field) == value


@pytest.mark.parametrize("field", ["nz_relevance", "india_relevance", "member_relevance"])
@pytest.mark.parametrize("value", [-1, 6, 100])
def test_relevance_rejects_values_outside_range(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Candidate(run_id=RUN_ID, headline="h", **{field: value})


def test_relevance_defaults_to_unset() -> None:
    candidate = Candidate(run_id=RUN_ID, headline="h")
    assert candidate.nz_relevance is None
    assert candidate.india_relevance is None
    assert candidate.member_relevance is None
