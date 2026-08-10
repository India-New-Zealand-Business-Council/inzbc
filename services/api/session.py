"""HTTP transport for sessions (#42): the cookie, the CSRF check, and `/api/session`.

Split from `auth.py` the same way `runs.py` is split from `persistence.py`: the rules about who
may do what are decided there and are testable without FastAPI, and this module only carries
them over HTTP. Nothing here decides authority.

**The dependency is the point.** `require_principal` is what a router declares to stop accepting
a caller-supplied `actor_id`. Until routers adopt it, the identity in an audit row is still a
claim; adopting it is a per-router change because each one's request model has to lose its
`actor_id` field, and that is an API contract change rather than a drop-in.

**Sign-in is deliberately incomplete.** `POST /api/session` takes an already-verified GitHub
login, which is not something a browser may assert. The OAuth handshake that turns a GitHub
redirect into a verified login is not built (#42 follow-up), so this endpoint is gated behind
`SESSION_TRUSTED_SIGNIN` and refuses entirely unless it is set. That keeps the route usable for
local development and integration tests without shipping an endpoint that would let anyone
become anyone.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

from services.api.auth import (
    ABSOLUTE_LIFETIME,
    AuthenticationError,
    NotAuthorisedError,
    Principal,
    SessionRepository,
)

router = APIRouter(prefix="/api/session", tags=["Session"])

# Host-only, HttpOnly, SameSite=Lax, Secure - ADR-0004. Named without a `__Host-` prefix only
# because local development is not HTTPS; the prefix is worth adding once deployed.
SESSION_COOKIE = "inzbc_session"
CSRF_HEADER = "X-CSRF-Token"

# Every method that can change state. GET/HEAD/OPTIONS are excluded because they must not, and
# a CSRF token on a read would train callers to send it everywhere.
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def get_session_repository() -> SessionRepository:
    """Overridden in tests, matching how the other routers take their repository."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="DATABASE_URL is not configured"
        )
    return SessionRepository(database_url)


def require_principal(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    repository: SessionRepository = Depends(get_session_repository),
) -> Principal:
    """Resolves the session cookie, or refuses.

    A router that declares this dependency cannot be called anonymously, and gets an identity
    established from server-side state rather than from the request body.
    """
    if not session_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="no session")
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
    if not submitted or submitted != principal.csrf_token:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="missing or invalid CSRF token"
        )
    return principal


class SignInIn(BaseModel):
    github_login: str = Field(min_length=1)


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


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def sign_in(
    body: SignInIn,
    response: Response,
    repository: SessionRepository = Depends(get_session_repository),
) -> SessionOut:
    """Issues a session for a GitHub login.

    Refuses unless `SESSION_TRUSTED_SIGNIN` is set, because without the OAuth handshake this
    endpoint would take the caller's word for who they are. Fail-closed: the check is for the
    variable being present and true, so an unset or empty value refuses.
    """
    if os.getenv("SESSION_TRUSTED_SIGNIN", "").lower() not in {"1", "true", "yes"}:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "GitHub OAuth sign-in is not implemented; this endpoint is available only "
                "with SESSION_TRUSTED_SIGNIN set, for local development and tests"
            ),
        )
    try:
        principal = repository.establish_session(body.github_login)
    except NotAuthorisedError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    response.set_cookie(
        key=SESSION_COOKIE,
        value=principal.session_id,
        max_age=int(ABSOLUTE_LIFETIME.total_seconds()),
        httponly=True,   # a script cannot read it, so an XSS cannot exfiltrate the session
        secure=True,     # never sent over plain HTTP
        samesite="lax",  # not "strict": a link from an email into the app should still work
    )
    return _to_out(principal)


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
    repository: SessionRepository = Depends(get_session_repository),
) -> None:
    """Ends the session server-side and clears the cookie.

    Deliberately not behind the CSRF check. A forged sign-out is a nuisance rather than a breach,
    and refusing to sign someone out because a token was missing is the worse failure.
    """
    repository.end_session(principal.session_id)
    response.delete_cookie(key=SESSION_COOKIE, httponly=True, secure=True, samesite="lax")
