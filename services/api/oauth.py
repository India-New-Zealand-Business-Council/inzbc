"""The GitHub OAuth handshake (#42), the last piece before anyone can sign in through a browser.

Everything either side of this already existed. `auth.py` turns a verified GitHub login into a
session against the allowlist; `session.py` carries that session over HTTP. What was missing was
the part that establishes the login is genuinely the caller's, so sessions had to be issued out of
band by `scripts/dev_session.py`.

**GitHub authenticates; it never authorises.** A successful handshake proves who the caller is on
GitHub and nothing more. The login is matched against `users.github_login`, and no active row means
403 with no session, per ADR-0004. That order matters: an authenticated GitHub user is not an
authorised INZBC user, and conflating the two would turn "has a GitHub account" into "may read the
intelligence platform".

**The access token is used once and discarded.** It is exchanged for the login and never stored,
so a database leak cannot yield GitHub credentials, and the platform never holds a token it could
be tempted to use for anything else.

Configuration, all required for the routes to work at all:
- `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET` - from the org-owned OAuth app
- `GITHUB_OAUTH_REDIRECT_URI` - must match the app's registered callback exactly
- `SESSION_COOKIE_SECURE` - optional, `false` only for local HTTP development

Absent any of them the routes return 503 rather than half-working, because a partially configured
sign-in is worse than an obviously absent one.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse

from services.api.auth import ABSOLUTE_LIFETIME, NotAuthorisedError, SessionRepository
from services.api.session import SESSION_COOKIE, get_session_repository

router = APIRouter(prefix="/api/auth", tags=["Session"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

# The `state` parameter, held in its own short-lived cookie. This is CSRF protection for the
# handshake itself: without it an attacker can send a victim a callback URL carrying the
# attacker's authorisation code, and the victim ends up logged into the attacker's account. The
# cookie is host-only and HttpOnly, so the value cannot be read or set by script.
STATE_COOKIE = "inzbc_oauth_state"
STATE_TTL_SECONDS = 600

# Only what the allowlist needs. `read:user` would also return private profile fields the platform
# has no use for, and asking for less is the whole point of a scope.
SCOPE = "read:user"

_TOKEN_BYTES = 32
_HTTP_TIMEOUT = 10.0


@dataclass(frozen=True)
class OAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str


def _config() -> OAuthConfig:
    """Reads the OAuth configuration, or refuses.

    Every value is required. A handshake missing its secret would fail at the token exchange with
    an error from GitHub rather than from us, which is a worse thing to debug than a 503 that says
    what is unset.
    """
    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("GITHUB_OAUTH_REDIRECT_URI", "").strip()
    missing = [
        name
        for name, value in (
            ("GITHUB_OAUTH_CLIENT_ID", client_id),
            ("GITHUB_OAUTH_CLIENT_SECRET", client_secret),
            ("GITHUB_OAUTH_REDIRECT_URI", redirect_uri),
        )
        if not value
    ]
    if missing:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"GitHub sign-in is not configured: {', '.join(missing)} unset",
        )
    return OAuthConfig(client_id, client_secret, redirect_uri)


def _cookie_secure() -> bool:
    """Secure by default. Only local HTTP development turns it off, and it has to say so."""
    return os.getenv("SESSION_COOKIE_SECURE", "true").strip().lower() not in {"0", "false", "no"}


@router.get("/github", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
def begin_github_sign_in(response: Response) -> RedirectResponse:
    """Starts the handshake: mint a state value, set it as a cookie, redirect to GitHub."""
    config = _config()
    state = secrets.token_urlsafe(_TOKEN_BYTES)

    redirect = RedirectResponse(
        url=(
            f"{GITHUB_AUTHORIZE_URL}"
            f"?client_id={config.client_id}"
            f"&redirect_uri={config.redirect_uri}"
            f"&scope={SCOPE}"
            f"&state={state}"
        ),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    redirect.set_cookie(
        key=STATE_COOKIE,
        value=state,
        max_age=STATE_TTL_SECONDS,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",  # not "strict": the callback is a cross-site navigation from github.com
    )
    return redirect


@router.get("/github/callback")
def complete_github_sign_in(
    response: Response,
    code: str = Query(..., min_length=1),
    state: str = Query(..., min_length=1),
    expected_state: str | None = Cookie(default=None, alias=STATE_COOKIE),
    repository: SessionRepository | None = Depends(get_session_repository),
) -> dict[str, str]:
    """Completes the handshake and issues a session, or refuses.

    Checked in this order, and the order is the point: the state before the code, because
    validating an attacker-supplied code first would mean exchanging it with GitHub before
    discovering the request was forged.
    """
    if repository is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="DATABASE_URL is not configured"
        )
    config = _config()

    # `compare_digest`, and a missing cookie refuses rather than being treated as "no state
    # expected". An attacker who can suppress the cookie must not thereby skip the check.
    if not expected_state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=(
                "sign-in state did not match. Start again from /api/auth/github rather than "
                "following a callback link from elsewhere."
            ),
        )

    login = _exchange_code_for_login(code, config)

    try:
        principal = repository.establish_session(login)
    except NotAuthorisedError as error:
        # Authenticated on GitHub, not authorised here. 403 rather than 401: signing in again
        # changes nothing, and the message deliberately does not say whether the login exists in
        # `users`, which would let anyone probe the allowlist.
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    response.set_cookie(
        key=SESSION_COOKIE,
        value=principal.session_id,
        max_age=int(ABSOLUTE_LIFETIME.total_seconds()),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )
    # The state cookie has done its job; leaving it set would let a later request reuse it.
    response.delete_cookie(key=STATE_COOKIE, httponly=True, samesite="lax")

    # The CSRF token has to reach the client somehow, and this is the one response that can carry
    # it: the session cookie is HttpOnly, so script cannot read it there.
    return {"user_id": principal.user_id, "name": principal.name,
            "csrf_token": principal.csrf_token}


def _exchange_code_for_login(code: str, config: OAuthConfig) -> str:
    """Exchanges the authorisation code for the caller's GitHub login.

    The access token lives only inside this function. It is used for one request and never
    returned, logged or stored: the platform needs the login, not standing access to the account.
    """
    with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
        token_response = client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "code": code,
                "redirect_uri": config.redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        if token_response.status_code != 200:
            # Deliberately not forwarding GitHub's body: it can echo the code back, and this
            # response may be rendered in a browser.
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, detail="GitHub rejected the sign-in exchange"
            )

        access_token = token_response.json().get("access_token")
        if not access_token:
            # GitHub returns 200 with an `error` field for an expired or reused code.
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="the sign-in code was rejected; it may have expired or been used already",
            )

        user_response = client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        if user_response.status_code != 200:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, detail="could not read the GitHub account"
            )

        login = (user_response.json().get("login") or "").strip()
        if not login:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, detail="GitHub returned no account login"
            )
        return login
