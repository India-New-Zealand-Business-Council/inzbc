"""HTTP transport for sessions (#42): the cookie, the CSRF check, and `/api/session`.

Split from `auth.py` the same way `runs.py` is split from `persistence.py`: the rules about who
may do what are decided there and are testable without FastAPI, and this module only carries
them over HTTP. Nothing here decides authority.

**The dependency is the point.** `require_principal` is what a router declares to stop accepting
a caller-supplied `actor_id`. Until routers adopt it, the identity in an audit row is still a
claim; adopting it is a per-router change because each one's request model has to lose its
`actor_id` field, and that is an API contract change rather than a drop-in.

**There is no sign-in route here, deliberately.** The OAuth handshake that turns a GitHub redirect
into a verified login is not built yet, and an HTTP endpoint that takes a `github_login` on trust
is account impersonation however carefully it is gated. Sessions are issued out of band by
`scripts/dev_session.py`, which needs database access and cannot be reached over the network.
"""

from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel

from services.api.auth import (
    AuthenticationError,
    NotAuthorisedError,
    Principal,
    SessionRepository,
    require_roles,
)

router = APIRouter(prefix="/api/session", tags=["Session"])

# Host-only, HttpOnly, SameSite=Lax, Secure - ADR-0004. Named without a `__Host-` prefix only
# because local development is not HTTPS; the prefix is worth adding once deployed.
SESSION_COOKIE = "inzbc_session"
CSRF_HEADER = "X-CSRF-Token"

# Every method that can change state. GET/HEAD/OPTIONS are excluded because they must not, and
# a CSRF token on a read would train callers to send it everywhere.
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def get_session_repository() -> SessionRepository | None:
    """Overridden in tests, matching how the other routers take their repository.

    Returns `None` rather than raising when `DATABASE_URL` is unset. FastAPI resolves
    sub-dependencies before the function that declares them, so raising here answered an
    anonymous, cookie-less request with 503 and told an unauthenticated caller whether the
    database is configured. The 401 has to come first; the 503 is raised below, only once there
    is a cookie worth resolving.
    """
    database_url = os.getenv("DATABASE_URL")
    return SessionRepository(database_url) if database_url else None


def require_principal(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    repository: SessionRepository | None = Depends(get_session_repository),
) -> Principal:
    """Resolves the session cookie, or refuses.

    A router that declares this dependency cannot be called anonymously, and gets an identity
    established from server-side state rather than from the request body.
    """
    if not session_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="no session")
    if repository is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="DATABASE_URL is not configured"
        )
    try:
        return repository.resolve(session_id)
    except AuthenticationError as error:
        # 401, not 403: signing in again would fix this.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    except NotAuthorisedError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error


def require_csrf(
    principal: Principal = Depends(require_principal),
    submitted: str | None = Header(default=None, alias=CSRF_HEADER),
) -> Principal:
    """Double-submit check for state-changing requests, per ADR-0004.

    SameSite=Lax alone is not enough: it still permits a top-level POST navigation from another
    site, which is exactly the shape of a form-submission CSRF. The token is compared to the one
    stored with the session, so an attacker who can make the browser send the cookie still cannot
    supply the header.

    Returns the principal so a router can declare this instead of `require_principal` and get
    both checks in one dependency rather than remembering two.
    """
    # `compare_digest` rather than `!=`. The timing leak here is not credibly exploitable (the
    # database round trip above dwarfs it, and the token has 256 bits of entropy), but a
    # constant-time compare on a secret costs nothing and removes the question.
    if not submitted or not secrets.compare_digest(submitted, principal.csrf_token):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="missing or invalid CSRF token"
        )
    return principal


class SessionOut(BaseModel):
    user_id: str
    name: str
    roles: list[str]
    csrf_token: str


def _to_out(principal: Principal) -> SessionOut:
    # Sorted so the response is stable; a set's order is not.
    return SessionOut(
        user_id=principal.user_id,
        name=principal.name,
        roles=sorted(principal.roles),
        csrf_token=principal.csrf_token,
    )


# There is deliberately no sign-in route.
#
# An earlier version had `POST /api/session` take a `github_login` and issue a session, gated
# behind an environment variable. That is account impersonation one config line away: anyone who
# copied the flag into a deployed environment would let an attacker post an allowlisted
# approver's public GitHub username and receive that person's session. A gate whose failure mode
# is "become the CEO" does not belong in a mounted router.
#
# Until the OAuth handshake exists, sessions are issued out of band by `scripts/dev_session.py`,
# which requires database access and cannot be reached over HTTP. Tests override
# `get_session_repository` and never needed the endpoint.


@router.get("", response_model=SessionOut)
def whoami(principal: Principal = Depends(require_principal)) -> SessionOut:
    """Who the current session belongs to, and the CSRF token to send with writes.

    A UI needs this to know which controls to show. It is not the authorisation check: the server
    re-checks on every write, because a hidden button is a hint and not a control.
    """
    return _to_out(principal)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(
    response: Response,
    principal: Principal = Depends(require_principal),
    repository: SessionRepository | None = Depends(get_session_repository),
) -> None:
    """Ends the session server-side and clears the cookie.

    Deliberately not behind the CSRF check. A forged sign-out is a nuisance rather than a breach,
    and refusing to sign someone out because a token was missing is the worse failure.
    """
    if repository is not None:
        repository.end_session(principal.session_id)
    response.delete_cookie(key=SESSION_COOKIE, httponly=True, secure=True, samesite="lax")


def _enforce_roles(principal: Principal, allowed: tuple[str, ...]) -> Principal:
    try:
        require_roles(principal, *allowed)
    except NotAuthorisedError as error:
        # 403, not 401: the caller is authenticated and refused. Signing in again changes nothing.
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    return principal


def read_access(*allowed: str):
    """Dependency for a read route: a valid session, held by one of `allowed`.

    Exists so a route declares its authority in its own signature rather than calling a check in
    its body. A check in the body is one a new route can forget; a dependency is visible in the
    route's dependency graph, which is what `test_router_auth.py` enumerates.
    """

    def dependency(principal: Principal = Depends(require_principal)) -> Principal:
        return _enforce_roles(principal, allowed)

    return dependency


def write_access(*allowed: str):
    """Dependency for a write route: a valid session, a matching CSRF token, and one of `allowed`.

    Authentication, CSRF and authorisation in one declaration, because separating them is how a
    route ends up with two of the three. That is not hypothetical: `require_roles` was written,
    tested and left unwired for the whole of #42, so every authenticated caller could do
    everything regardless of role until this landed.
    """

    def dependency(principal: Principal = Depends(require_csrf)) -> Principal:
        return _enforce_roles(principal, allowed)

    return dependency
