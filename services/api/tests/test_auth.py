"""Authorisation rules for #42.

Split deliberately from the session-storage tests: these need no database, so the rules that
decide whether an action is permitted are provable without Postgres, and stay provable if the
storage layer changes. The session lifecycle tests live in `test_auth_sessions.py` and are
skipped without a database, matching the other Postgres-backed suites here.

Every test below is a refusal or a permission the acceptance criteria name, not a restatement of
the implementation.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from services.api.auth import (
    NotAuthorisedError,
    Principal,
    SelfApprovalError,
    refuse_self_review,
    require_roles,
)


def principal(*roles: str, user_id: str = "11111111-1111-1111-1111-111111111111") -> Principal:
    return Principal(
        user_id=user_id,
        name="Test User",
        roles=frozenset(roles),
        session_id="session-id",
        csrf_token="csrf-token",
    )


def test_a_held_role_permits_the_action() -> None:
    require_roles(principal("Analyst"), "Analyst")


def test_any_one_of_several_allowed_roles_is_enough() -> None:
    require_roles(principal("Reviewer"), "SIP Owner", "Reviewer")


def test_a_missing_role_is_refused() -> None:
    with pytest.raises(NotAuthorisedError):
        require_roles(principal("Analyst"), "Reviewer")


def test_holding_no_roles_is_refused() -> None:
    with pytest.raises(NotAuthorisedError):
        require_roles(principal(), "Analyst")


def test_naming_no_allowed_roles_refuses_rather_than_permitting_everything() -> None:
    """Fail-closed. The likeliest cause is a caller that forgot to name the roles, and a
    permissive default there would silently open an endpoint nobody meant to open."""
    with pytest.raises(NotAuthorisedError):
        require_roles(principal("SIP Owner"))


def test_the_refusal_names_what_was_required() -> None:
    """An operator who cannot act needs to know which role would let them, otherwise the only
    way to find out is to read the source."""
    with pytest.raises(NotAuthorisedError, match="Reviewer"):
        require_roles(principal("Analyst"), "Reviewer")


def test_the_author_cannot_review_their_own_work() -> None:
    """BR8 and ADR-0005: a control one person can execute end to end is not a control."""
    actor = principal("Reviewer", user_id="22222222-2222-2222-2222-222222222222")
    with pytest.raises(SelfApprovalError):
        refuse_self_review(actor, "22222222-2222-2222-2222-222222222222")


def test_holding_the_reviewer_role_does_not_override_self_review() -> None:
    """The role is necessary and not sufficient. Someone who holds every role, which is the
    stated steady state after the placement ends, still cannot review their own output."""
    everyone = principal(
        "Analyst", "Reviewer", "SIP Owner", user_id="33333333-3333-3333-3333-333333333333"
    )
    with pytest.raises(SelfApprovalError):
        refuse_self_review(everyone, "33333333-3333-3333-3333-333333333333")


def test_a_different_author_may_be_reviewed() -> None:
    refuse_self_review(principal("Reviewer", user_id="aaaa"), "bbbb")


def test_an_unattributed_record_may_be_reviewed() -> None:
    """`None` means the record has no recorded author, which is not the same as it being the
    reviewer's own. Refusing here would make pre-existing rows permanently unreviewable."""
    refuse_self_review(principal("Reviewer", user_id="aaaa"), None)


def test_self_approval_is_a_kind_of_authorisation_failure() -> None:
    """So a caller that only cares about permitted-or-not can catch one type, while a caller
    that wants to explain *why* can catch the specific one."""
    assert issubclass(SelfApprovalError, NotAuthorisedError)


def test_a_principal_cannot_widen_its_own_authority() -> None:
    """Frozen, so a request handler cannot assign itself a role partway through.

    Asserting the specific `FrozenInstanceError` rather than bare `Exception`: a blind assertion
    here would still pass if the line failed for some unrelated reason, which would leave the
    test green while the protection it claims to prove had been removed.
    """
    with pytest.raises(FrozenInstanceError):
        principal("Analyst").roles = frozenset({"SIP Owner"})  # type: ignore[misc]
