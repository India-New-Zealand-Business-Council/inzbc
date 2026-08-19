"""The GitHub OAuth handshake (#42).

No network and no database: `httpx` is stubbed and the repository is overridden, because what is
under test is the handshake's refusals, not GitHub's behaviour or session storage. Those are
covered in `test_auth_sessions.py` against real Postgres.

Every test here is a refusal or the one path that should succeed. The refusals matter more: this
is the only route that turns an anonymous caller into an authenticated one, so each check is the
difference between a sign-in and an account takeover.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api.auth import NotAuthorisedError, Principal
from services.api.oauth import STATE_COOKIE, router
from services.api.session import SESSION_COOKIE, get_session_repository

PRINCIPAL = Principal(
    user_id="11111111-1111-1111-1111-111111111111",
    name="Test User",
    roles=frozenset({"Analyst"}),
    session_id="session-abc",
    csrf_token="csrf-xyz",
)

CONFIG = {
    "GITHUB_OAUTH_CLIENT_ID": "client-id",
    "GITHUB_OAUTH_CLIENT_SECRET": "client-secret",
    "GITHUB_OAUTH_REDIRECT_URI": "https://example.test/api/auth/github/callback",
    "SESSION_COOKIE_SECURE": "false",
}


class FakeRepository:
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.logins: list[str] = []

    def establish_session(self, github_login: str) -> Principal:
        self.logins.append(github_login)
        if self._error:
            raise self._error
        return PRINCIPAL


class FakeGitHub:
    """Stands in for `httpx.Client`, recording what was sent so the tests can assert on it."""

    def __init__(self, *, token: str | None = "gho_token", login: str | None = "someone",
                 token_status: int = 200, user_status: int = 200) -> None:
        self.token = token
        self.login = login
        self.token_status = token_status
        self.user_status = user_status
        self.posted: dict = {}
        self.auth_header: str | None = None

    def __enter__(self) -> FakeGitHub:  # noqa: PYI034 - a stub, not a real context manager
        return self

    def __exit__(self, *exc) -> None:
        return None

    def post(self, url: str, data: dict, headers: dict):
        self.posted = data
        body = {"access_token": self.token} if self.token else {"error": "bad_verification_code"}
        return _Response(self.token_status, body)

    def get(self, url: str, headers: dict):
        self.auth_header = headers.get("Authorization")
        return _Response(self.user_status, {"login": self.login} if self.login else {})


class _Response:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in CONFIG.items():
        monkeypatch.setenv(key, value)


def build_client(repository: FakeRepository, github: FakeGitHub | None = None,
                 monkeypatch: pytest.MonkeyPatch | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session_repository] = lambda: repository
    if github is not None and monkeypatch is not None:
        monkeypatch.setattr("services.api.oauth.httpx.Client", lambda **_: github)
    return TestClient(app)


def test_sign_in_is_unavailable_until_it_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """503 rather than a half-working handshake. A missing secret would otherwise surface as an
    error from GitHub, which is a worse thing to debug than one that names the unset variable."""
    for key in CONFIG:
        monkeypatch.delenv(key, raising=False)
    response = build_client(FakeRepository()).get("/api/auth/github", follow_redirects=False)
    assert response.status_code == 503
    assert "GITHUB_OAUTH_CLIENT_ID" in response.json()["detail"]


def test_beginning_sign_in_redirects_to_github_and_sets_state(configured: None) -> None:
    response = build_client(FakeRepository()).get("/api/auth/github", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].startswith("https://github.com/login/oauth/authorize")
    assert "scope=read:user" in response.headers["location"]
    assert STATE_COOKIE in response.headers["set-cookie"]


def test_the_state_cookie_is_not_readable_by_script(configured: None) -> None:
    """It is CSRF protection for the handshake. A value script can read is a value an attacker
    who has any script execution can also read and replay."""
    response = build_client(FakeRepository()).get("/api/auth/github", follow_redirects=False)
    assert "httponly" in response.headers["set-cookie"].lower()


def test_two_sign_ins_never_share_a_state_value(configured: None) -> None:
    client = build_client(FakeRepository())
    first = client.get("/api/auth/github", follow_redirects=False).headers["set-cookie"]
    second = client.get("/api/auth/github", follow_redirects=False).headers["set-cookie"]
    assert first != second


def test_a_callback_with_no_state_cookie_is_refused(configured: None) -> None:
    """The attack this stops: an attacker sends a victim a callback URL carrying the attacker's
    authorisation code, and the victim ends up signed into the attacker's account. Suppressing
    the cookie must not skip the check."""
    response = build_client(FakeRepository()).get(
        "/api/auth/github/callback?code=abc&state=anything"
    )
    assert response.status_code == 403


def test_a_callback_whose_state_does_not_match_is_refused(configured: None) -> None:
    client = build_client(FakeRepository())
    client.get("/api/auth/github", follow_redirects=False)
    response = client.get("/api/auth/github/callback?code=abc&state=not-the-state")
    assert response.status_code == 403


def test_the_code_is_never_exchanged_when_the_state_is_wrong(
    configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Order matters. Exchanging first would send an attacker-supplied code to GitHub before
    discovering the request was forged."""
    github = FakeGitHub()
    client = build_client(FakeRepository(), github, monkeypatch)
    client.get("/api/auth/github", follow_redirects=False)
    client.get("/api/auth/github/callback?code=abc&state=wrong")
    assert github.posted == {}


def test_a_valid_callback_issues_a_session(
    configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = FakeRepository()
    github = FakeGitHub(login="someone")
    client = build_client(repository, github, monkeypatch)

    begin = client.get("/api/auth/github", follow_redirects=False)
    state = begin.headers["set-cookie"].split(f"{STATE_COOKIE}=")[1].split(";")[0]
    response = client.get(f"/api/auth/github/callback?code=abc&state={state}")

    assert response.status_code == 200
    assert repository.logins == ["someone"]
    assert response.json()["csrf_token"] == PRINCIPAL.csrf_token
    assert SESSION_COOKIE in response.headers["set-cookie"]


def test_the_access_token_is_used_once_and_not_returned(
    configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The platform needs the login, not standing access to the account. A token in the response
    body, or stored, would be a GitHub credential this system has no reason to hold."""
    github = FakeGitHub(token="gho_secret_value")
    client = build_client(FakeRepository(), github, monkeypatch)
    begin = client.get("/api/auth/github", follow_redirects=False)
    state = begin.headers["set-cookie"].split(f"{STATE_COOKIE}=")[1].split(";")[0]

    response = client.get(f"/api/auth/github/callback?code=abc&state={state}")

    assert github.auth_header == "Bearer gho_secret_value"
    assert "gho_secret_value" not in response.text


def test_a_login_not_on_the_allowlist_is_refused(
    configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-0004: GitHub authenticates, it never authorises. Without this, anyone with a GitHub
    account could read the intelligence platform."""
    repository = FakeRepository(error=NotAuthorisedError("not an active INZBC user"))
    client = build_client(repository, FakeGitHub(login="stranger"), monkeypatch)
    begin = client.get("/api/auth/github", follow_redirects=False)
    state = begin.headers["set-cookie"].split(f"{STATE_COOKIE}=")[1].split(";")[0]

    response = client.get(f"/api/auth/github/callback?code=abc&state={state}")

    assert response.status_code == 403
    assert SESSION_COOKIE not in response.headers.get("set-cookie", "")


def test_a_rejected_code_does_not_become_a_session(
    configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GitHub returns 200 with an `error` field for an expired or reused code, so a naive read of
    the status would treat a refusal as success."""
    client = build_client(FakeRepository(), FakeGitHub(token=None), monkeypatch)
    begin = client.get("/api/auth/github", follow_redirects=False)
    state = begin.headers["set-cookie"].split(f"{STATE_COOKIE}=")[1].split(";")[0]

    response = client.get(f"/api/auth/github/callback?code=used-already&state={state}")
    assert response.status_code == 403


def test_an_account_with_no_login_is_refused(
    configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = build_client(FakeRepository(), FakeGitHub(login=None), monkeypatch)
    begin = client.get("/api/auth/github", follow_redirects=False)
    state = begin.headers["set-cookie"].split(f"{STATE_COOKIE}=")[1].split(";")[0]

    assert client.get(f"/api/auth/github/callback?code=abc&state={state}").status_code == 502
