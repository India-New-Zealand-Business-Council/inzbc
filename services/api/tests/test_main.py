from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from services.api.main import ActionRequiredOut, FtaQueryResponse, app

client = TestClient(app)


def test_uncovered_product_warning_survives_the_http_response() -> None:
    response = client.get("/api/fta/query", params={"q": "steel exports"})
    assert response.status_code == 200
    answer = response.json()["answers"][0]
    assert answer["id"] == "FTA-002"
    assert "no product-specific match" in answer["coverage_warning"]
    assert "Contact INZBC" in answer["coverage_warning"]


def test_matched_query_returns_answers_and_no_escalation() -> None:
    body = client.get("/api/fta/query", params={"q": "wool"}).json()
    assert body["status"] == "matched"
    assert body["query"] == "wool"
    assert body["action_required"] is None
    assert len(body["answers"]) == 1
    assert body["answers"][0]["topic"] == "Wool"
    assert body["answers"][0]["confidence"] == "High"


def test_sector_query_returns_every_matching_answer() -> None:
    body = client.get("/api/fta/query", params={"q": "dairy"}).json()
    assert body["status"] == "matched"
    topics = {a["topic"] for a in body["answers"]}
    assert "Dairy - peptones" in topics
    assert len(topics) > 1


def test_no_match_returns_200_with_escalation_not_an_error() -> None:
    # A no-match is a designed outcome, not a failure: 404 would push callers into an error
    # branch that discards the escalation guidance.
    response = client.get("/api/fta/query", params={"q": "semiconductor export controls"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_match"
    assert body["answers"] == []
    assert body["action_required"]["confidence"] == "Action Required"
    assert "INZBC" in body["action_required"]["escalation_path"]


def test_no_match_payload_carries_no_evidence_fields() -> None:
    # The structural guarantee from apps/fta/explainer, held across the wire.
    body = client.get("/api/fta/query", params={"q": "semiconductor export controls"}).json()
    action = body["action_required"]
    for evidence_field in ("topic", "sector", "treatment", "citation", "verified_at", "confirmed"):
        assert evidence_field not in action


def test_stopword_only_query_escalates_rather_than_matching() -> None:
    body = client.get("/api/fta/query", params={"q": "the and of"}).json()
    assert body["status"] == "no_match"


def test_every_answer_carries_the_approved_disclaimer() -> None:
    body = client.get("/api/fta/query", params={"q": "wine"}).json()
    for answer in body["answers"]:
        assert "indicate this rather than speculate" in answer["disclaimer"]
        assert "[[" not in answer["disclaimer"]


def test_missing_query_is_rejected() -> None:
    assert client.get("/api/fta/query").status_code == 422


def test_overlong_query_is_rejected() -> None:
    assert client.get("/api/fta/query", params={"q": "x" * 501}).status_code == 422


@pytest.mark.parametrize(
    ("status", "answers", "action_required", "reason"),
    [
        ("matched", [], None, "matched with no answers"),
        ("no_match", [], None, "no_match without escalation"),
    ],
)
def test_envelope_invariant_is_enforced(
    status: str, answers: list, action_required: ActionRequiredOut | None, reason: str
) -> None:
    # The status tag and the payload cannot disagree, so a client branching on `status` is safe.
    with pytest.raises(ValidationError):
        FtaQueryResponse(status=status, query="q", answers=answers, action_required=action_required)


def test_no_match_envelope_cannot_also_carry_answers() -> None:
    # The inverse of the above: escalating while still shipping findings would let a client
    # render both, which is the ambiguity the status tag exists to remove.
    body = client.get("/api/fta/query", params={"q": "wool"}).json()
    with pytest.raises(ValidationError):
        FtaQueryResponse(
            status="no_match",
            query="wool",
            answers=[body["answers"][0]],
            action_required={
                "message": "m", "next_step": "n", "escalation_path": "e",
                "status_line": "s", "jurisdiction": "j", "disclaimer": "d",
                "confidence": "Action Required", "confidence_meaning": "cm",
            },
        )


def test_matched_envelope_cannot_also_escalate() -> None:
    body = client.get("/api/fta/query", params={"q": "wool"}).json()
    answer = body["answers"][0]
    with pytest.raises(ValidationError):
        FtaQueryResponse(
            status="matched",
            query="wool",
            answers=[answer],
            action_required={
                "message": "m", "next_step": "n", "escalation_path": "e",
                "status_line": "s", "jurisdiction": "j", "disclaimer": "d",
                "confidence": "Action Required", "confidence_meaning": "cm",
            },
        )


def test_health_probe() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_openapi_documents_the_query_endpoint() -> None:
    # Task 0.6 generates the TypeScript client from this schema, so it has to be well formed.
    schema = client.get("/openapi.json").json()
    assert schema["openapi"].startswith("3.")
    operation = schema["paths"]["/api/fta/query"]["get"]
    assert operation["parameters"][0]["name"] == "q"
    assert "FtaQueryResponse" in str(operation["responses"]["200"])


def test_a_tariff_query_returns_the_structured_figures_not_only_prose() -> None:
    """#185: the Explainer must answer a tariff question *from* the data.

    The structured fields reached `ExplainerAnswer` in #273 but not `AnswerOut`, so every HTTP
    caller still received `treatment` prose and had to re-parse it. `extra="forbid"` meant they
    could not appear by accident, so nothing failed and the gap was invisible from the API.
    """
    answer = client.get("/api/fta/query", params={"q": "wool"}).json()["answers"][0]
    assert answer["current_tariff"] == "2.75%"
    assert answer["final_tariff"] == "0% (eliminated)"
    assert answer["implementation_period_years"] == 0
    assert answer["direction"] == "NZ exports to India"


def test_an_entry_with_no_sourced_figure_returns_null_not_zero() -> None:
    """Excluded dairy has no product-level tariff line in the source.

    `None` here means "not sourced", never "zero" or "unchanged". Serving 0 would be inventing a
    figure for the one product the FTA explicitly leaves out, which is the worst place to guess.
    """
    answer = client.get("/api/fta/query", params={"q": "dairy"}).json()["answers"][0]
    assert answer["current_tariff"] is None
    assert answer["final_tariff"] is None
    # The qualitative claim is still sourced, so the answer is not empty.
    assert answer["treatment"]
    assert answer["citation"]


def test_default_fta_query_serves_public_depth_and_withholds_internal_fields() -> None:
    """#392: unauthenticated `/api/fta/query` defaults to `public` depth and withholds
    `source_tier` and `notes`."""
    body = client.get("/api/fta/query", params={"q": "dairy"}).json()
    assert body["depth"] == "public"
    for answer in body["answers"]:
        assert answer["source_tier"] is None
        assert answer["notes"] is None


@pytest.mark.parametrize("depth", ["member", "internal"])
def test_non_public_fta_depths_refuse_anonymous_callers(depth: str) -> None:
    response = client.get("/api/fta/query", params={"q": "wool", "depth": depth})
    assert response.status_code == 401


def test_a_stale_session_cookie_does_not_block_the_public_answer() -> None:
    stale = TestClient(app, cookies={"inzbc_session": "expired-or-unknown"})
    response = stale.get("/api/fta/query", params={"q": "wool"})
    assert response.status_code == 200
    assert response.json()["depth"] == "public"


def test_member_depth_serves_authenticated_member_and_withholds_internal_notes() -> None:
    from services.api.auth import Principal
    from services.api.main import resolve_fta_principal

    app.dependency_overrides[resolve_fta_principal] = lambda: Principal(
        user_id="00000000-0000-0000-0000-0000000000b1",
        name="Board Viewer User",
        roles=frozenset({"Board Viewer"}),
        session_id="s-board",
        csrf_token="c-board",
    )
    try:
        response = client.get("/api/fta/query", params={"q": "dairy", "depth": "member"})
        assert response.status_code == 200
        body = response.json()
        assert body["depth"] == "member"
        for answer in body["answers"]:
            assert answer["source_tier"] is None
            assert answer["notes"] is None
    finally:
        app.dependency_overrides.pop(resolve_fta_principal, None)


def test_internal_depth_refuses_underprivileged_role_and_serves_reviewer() -> None:
    from services.api.auth import Principal
    from services.api.main import resolve_fta_principal

    app.dependency_overrides[resolve_fta_principal] = lambda: Principal(
        user_id="00000000-0000-0000-0000-0000000000b2",
        name="Secretariat User",
        roles=frozenset({"Secretariat"}),
        session_id="s-sec",
        csrf_token="c-sec",
    )
    try:
        denied = client.get("/api/fta/query", params={"q": "dairy", "depth": "internal"})
        assert denied.status_code == 403

        app.dependency_overrides[resolve_fta_principal] = lambda: Principal(
            user_id="00000000-0000-0000-0000-0000000000b3",
            name="Reviewer User",
            roles=frozenset({"Reviewer"}),
            session_id="s-rev",
            csrf_token="c-rev",
        )
        allowed = client.get("/api/fta/query", params={"q": "dairy", "depth": "internal"})
        assert allowed.status_code == 200
        body = allowed.json()
        assert body["depth"] == "internal"
        assert all(a["source_tier"] in {1, 2} for a in body["answers"])
        assert any(a["notes"] is not None for a in body["answers"])
    finally:
        app.dependency_overrides.pop(resolve_fta_principal, None)
