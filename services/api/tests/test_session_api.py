"""HTTP behaviour of `/api/session` and the auth dependencies (#42).

No database: the repository is replaced through FastAPI's dependency override, the same way the
other router tests here isolate their layer. What is under test is the mapping between auth
outcomes and HTTP - which failure is a 401 and which a 403, whether the cookie carries the right
flags, whether CSRF actually refuses - not the session storage, which `test_auth_sessions.py`
covers against real Postgres.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from services.api.auth import AuthenticationError, NotAuthorisedError, Principal
from services.api.session import (
    CSRF_HEADER,
    SESSION_COOKIE,
    get_session_repository,
    require_csrf,
    require_principal,
    router,
)

PRINCIPAL = Principal(
    user_id="11111111-1111-1111-1111-111111111111",
    name="Test User",
    roles=frozenset({"Analyst"}),
    session_id="session-abc",
    csrf_token="csrf-xyz",
)


class FakeRepository:
    """Records what it was asked, so tests can assert the router called the right thing."""

    def __init__(self, *, resolve_error: Exception | None = None,
                 establish_error: Exception | None = None) -> None:
        self._resolve_error = resolve_error
        self._establish_error = establish_error
        self.ended: list[str] = []

    def resolve(self, session_id: str) -> Principal:
        if self._resolve_error:
            raise self._resolve_error
        return PRINCIPAL

    def establish_session(self, github_login: str) -> Principal:
        if self._establish_error:
            raise self._establish_error
        return PRINCIPAL

    def end_session(self, session_id: str) -> None:
        self.ended.append(session_id)


def build_client(repository: FakeRepository) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    # A protected route that exists only for these tests, so the dependencies can be exercised
    # without depending on which real routers have adopted them yet.
    @app.post("/test/guarded")
    def guarded(principal: Principal = Depends(require_csrf)) -> dict:
        return {"user_id": principal.user_id}

    @app.get("/test/read")
    def read(principal: Principal = Depends(require_principal)) -> dict:
        return {"user_id": principal.user_id}

    app.dependency_overrides[get_session_repository] = lambda: repository
    return TestClient(app)


def test_no_cookie_is_401() -> None:
    """401 rather than 403: the caller has not identified themselves, and signing in would fix it."""
    response = build_client(FakeRepository()).get("/test/read")
    assert response.status_code == 401


def test_a_valid_cookie_resolves_the_caller() -> None:
    client = build_client(FakeRepository())
    client.cookies.set(SESSION_COOKIE, "session-abc")
    response = client.get("/test/read")
    assert response.status_code == 200
    assert response.json()["user_id"] == PRINCIPAL.user_id


def test_an_expired_session_is_401() -> None:
    client = build_client(FakeRepository(resolve_error=AuthenticationError("session expired")))
    client.cookies.set(SESSION_COOKIE, "stale")
    assert client.get("/test/read").status_code == 401


def test_a_deactivated_account_is_403_not_401() -> None:
    """The distinction matters: 401 invites the caller to sign in again, which for a deactivated
    account would be an endless loop. 403 says the identity is known and refused."""
    client = build_client(FakeRepository(resolve_error=NotAuthorisedError("no longer active")))
    client.cookies.set(SESSION_COOKIE, "session-abc")
    assert client.get("/test/read").status_code == 403


def test_a_write_without_a_csrf_token_is_refused() -> None:
    client = build_client(FakeRepository())
    client.cookies.set(SESSION_COOKIE, "session-abc")
    assert client.post("/test/guarded").status_code == 403


def test_a_write_with_the_wrong_csrf_token_is_refused() -> None:
    """The whole point of double-submit: holding the cookie is not enough."""
    client = build_client(FakeRepository())
    client.cookies.set(SESSION_COOKIE, "session-abc")
    response = client.post("/test/guarded", headers={CSRF_HEADER: "not-the-token"})
    assert response.status_code == 403


def test_a_write_with_the_right_csrf_token_is_allowed() -> None:
    client = build_client(FakeRepository())
    client.cookies.set(SESSION_COOKIE, "session-abc")
    response = client.post("/test/guarded", headers={CSRF_HEADER: PRINCIPAL.csrf_token})
    assert response.status_code == 200


def test_csrf_still_requires_a_session() -> None:
    """Order matters: a caller with a guessed token but no cookie must not get past."""
    response = build_client(FakeRepository()).post(
        "/test/guarded", headers={CSRF_HEADER: PRINCIPAL.csrf_token}
    )
    assert response.status_code == 401


def test_whoami_returns_roles_and_the_csrf_token() -> None:
    client = build_client(FakeRepository())
    client.cookies.set(SESSION_COOKIE, "session-abc")
    body = client.get("/api/session").json()
    assert body["roles"] == ["Analyst"]
    assert body["csrf_token"] == PRINCIPAL.csrf_token


def test_there_is_no_sign_in_route() -> None:
    """The endpoint was removed rather than gated.

    It took a `github_login` on trust, behind an environment variable. That is account
    impersonation one config line away: a flag copied into a deployed environment would let
    anyone post an allowlisted approver's public GitHub username and receive their session.
    Sessions are now issued by `scripts/dev_session.py`, which needs database access and is not
    reachable over HTTP. This test fails if anyone re-adds the route.
    """
    response = build_client(FakeRepository()).post(
        "/api/session", json={"github_login": "someone"}
    )
    assert response.status_code == 405, (
        "POST /api/session should not exist; a sign-in route that trusts a supplied login is "
        "account impersonation however it is gated"
    )


def test_sign_out_ends_the_session_and_clears_the_cookie() -> None:
    repository = FakeRepository()
    client = build_client(repository)
    client.cookies.set(SESSION_COOKIE, "session-abc")
    response = client.delete("/api/session")
    assert response.status_code == 204
    assert repository.ended == [PRINCIPAL.session_id]
    assert SESSION_COOKIE in response.headers["set-cookie"]


def test_sign_out_does_not_require_a_csrf_token() -> None:
    """A forged sign-out is a nuisance; refusing to sign someone out is the worse failure."""
    client = build_client(FakeRepository())
    client.cookies.set(SESSION_COOKIE, "session-abc")
    assert client.delete("/api/session").status_code == 204
