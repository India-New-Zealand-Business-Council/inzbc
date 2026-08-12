"""Every business route requires a session (#42).

**Why this file exists separately.** The root `conftest.py` installs an autouse fixture that
supplies a principal to `services.api.main.app`, so the router tests written before #42 keep
testing what they were written for instead of returning 401 everywhere. That fixture is also
exactly what would hide a route someone forgot to protect.

So this file opts out of the override and drives the real app. If a route is added without an
auth dependency, or an existing one loses it, the enumeration below fails.

The exploit this closes, found in adversarial review: an anonymous caller reads `GET /api/runs`,
which returns run ids and a valid `initiated_by` user UUID, then posts that UUID as `actor_id` to
`POST /api/runs/{id}/start` with any non-empty `approval_ref`. The launch gate accepts
unverifiable free text, and the audit trail records the impersonated user as having authorised
the run.
"""

from __future__ import annotations

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from services.api.auth import STAFF_READ
from services.api.main import app
from services.api.session import (
    CSRF_HEADER,
    SESSION_COOKIE,
    require_csrf,
    require_principal,
)

# Every role name the platform recognises, per database/schema.sql.
ALL_ROLES = STAFF_READ

# Public by design. The FTA explainer is published material with no personal data and no writes,
# and `/health` must answer before anything is configured or a load balancer cannot use it.
PUBLIC_PREFIXES = ("/health", "/api/fta", "/docs", "/openapi.json", "/redoc", "/static")

# Session management itself cannot require a session to *end*, and `GET /api/session` is how a
# caller discovers whether it has one. Both still resolve the cookie; they simply must not be in
# the enumeration below, which asserts a 401 for anonymous callers.
SESSION_PREFIX = "/api/session"


@pytest.fixture(autouse=True)
def _no_auth_override():
    """Undo conftest's principal for this file only, then restore it.

    Without this, every assertion here would pass for the wrong reason.
    """
    saved = dict(app.dependency_overrides)
    app.dependency_overrides.pop(require_principal, None)
    app.dependency_overrides.pop(require_csrf, None)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


def _walk(routes) -> list[APIRoute]:
    """Flatten nested routers.

    This FastAPI version keeps an included router as a single `_IncludedRouter` entry on
    `app.routes` rather than copying its `APIRoute`s up, so a flat scan finds only the routes
    declared directly on the app. Recursing is what makes this enumeration see the routers that
    matter; without it this file passed while checking two routes and proving nothing.
    """
    found: list[APIRoute] = []
    for route in routes:
        if isinstance(route, APIRoute):
            found.append(route)
        elif hasattr(route, "original_router"):
            # `_IncludedRouter` keeps the mounted router behind `original_router` instead of
            # exposing its routes directly.
            found.extend(_walk(route.original_router.routes))
        elif hasattr(route, "routes"):
            found.extend(_walk(route.routes))
    return found


def business_routes() -> list[tuple[str, str]]:
    """Every mounted route that is not deliberately public."""
    found = []
    for route in _walk(app.routes):
        if route.path.startswith(PUBLIC_PREFIXES) or route.path.startswith(SESSION_PREFIX):
            continue
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            found.append((method, route.path))
    return found


def test_there_are_business_routes_to_check() -> None:
    """Guards the guard: an enumeration that found nothing would pass silently and prove
    nothing, which is how this kind of test rots."""
    routes = business_routes()
    assert len(routes) >= 10, f"expected the runs/candidates/comms routes, found {routes}"
    paths = {path for _, path in routes}
    assert any(p.startswith("/api/runs") for p in paths)
    assert any(p.startswith("/api/candidates") for p in paths)
    assert any(p.startswith("/api/comms") for p in paths)


@pytest.mark.parametrize(
    ("method", "path"),
    business_routes(),
    ids=[f"{m} {p}" for m, p in business_routes()],
)
def test_no_business_route_answers_anonymously(method: str, path: str) -> None:
    """401 for every one. Not 200, and not 422 either.

    422 would mean the request was rejected for its shape before authentication was considered,
    which is the wrong order: it tells an anonymous caller what the endpoint expects.
    """
    concrete = path.replace("{run_id}", "00000000-0000-0000-0000-000000000001").replace(
        "{candidate_id}", "00000000-0000-0000-0000-000000000002"
    )
    with TestClient(app) as client:
        response = client.request(method, concrete, json={})
    assert response.status_code == 401, (
        f"{method} {path} answered {response.status_code} without a session. Every business "
        f"route must declare require_principal (reads) or require_csrf (writes)."
    )


@pytest.mark.parametrize(
    ("method", "path"),
    [(m, p) for m, p in business_routes() if m in {"POST", "PUT", "PATCH", "DELETE"}],
    ids=[f"{m} {p}" for m, p in business_routes() if m in {"POST", "PUT", "PATCH", "DELETE"}],
)
def test_no_write_route_accepts_a_caller_supplied_actor(method: str, path: str) -> None:
    """The identity must come from the session, so the field must not exist on the model.

    Left in place it would be worse than useless: a reviewer glancing at the request shape would
    reasonably assume it was being honoured, when the router now ignores it.
    """
    route = next(r for r in _walk(app.routes) if r.path == path and method in r.methods)
    for field_name in ("actor_id", "initiated_by"):
        for dependency in route.dependant.body_params:
            annotation = getattr(dependency.field_info, "annotation", None)
            fields = getattr(annotation, "model_fields", {})
            assert field_name not in fields, (
                f"{method} {path} still accepts {field_name!r} in its body. Identity comes from "
                f"the session; a body field invites impersonation."
            )


def _dependency_names(route: APIRoute) -> set[str]:
    """Every dependency function name in a route's graph, flattened."""
    names: set[str] = set()

    def walk(dependant) -> None:
        if dependant.call is not None:
            names.add(getattr(dependant.call, "__name__", ""))
            # `read_access`/`write_access` return a closure named `dependency`; the authority they
            # carry is in the closure's cells, not its name.
            closure = getattr(dependant.call, "__closure__", None) or ()
            for cell in closure:
                contents = cell.cell_contents
                if isinstance(contents, tuple) and all(isinstance(c, str) for c in contents):
                    names.update(contents)
        for sub in dependant.dependencies:
            walk(sub)

    walk(route.dependant)
    return names


@pytest.mark.parametrize(
    ("method", "path"),
    business_routes(),
    ids=[f"{m} {p}" for m, p in business_routes()],
)
def test_every_business_route_names_the_roles_it_requires(method: str, path: str) -> None:
    """Authentication without authorisation is not access control.

    This is the test that was missing. `require_roles` was written, unit-tested and never called
    from a single route for the whole of #42, so every authenticated caller could do everything
    regardless of role. Unit tests passed because they exercised the helper directly, and no
    integration test could fail on a function that is simply never invoked.

    Asserting the route's dependency graph carries at least one named role is what closes that:
    a new route with a session check and no authority fails here.
    """
    route = next(r for r in _walk(app.routes) if r.path == path and method in r.methods)
    names = _dependency_names(route)
    roles = names & set(ALL_ROLES)
    assert roles, (
        f"{method} {path} authenticates but names no role, so any signed-in user may call it. "
        f"Declare read_access(...) or write_access(...) with the roles that may."
    )


@pytest.mark.parametrize(
    ("method", "path"),
    [(m, p) for m, p in business_routes() if m in {"POST", "PUT", "PATCH", "DELETE"}],
    ids=[f"{m} {p}" for m, p in business_routes() if m in {"POST", "PUT", "PATCH", "DELETE"}],
)
def test_every_write_route_keeps_its_csrf_check(method: str, path: str) -> None:
    """Swapping `write_access` for `read_access` on a write would otherwise pass every other test
    here: the route would still refuse anonymous callers and still name roles, while silently
    losing the double-submit check."""
    route = next(r for r in _walk(app.routes) if r.path == path and method in r.methods)
    assert "require_csrf" in _dependency_names(route), (
        f"{method} {path} is a write route without require_csrf in its dependency graph."
    )


def test_the_contract_declares_the_session_cookie_and_csrf_token() -> None:
    """A published contract that omits how to authenticate is a contract a client cannot use.

    Before this, `schemas/openapi.json` carried no security schemes at all, so the generated
    TypeScript clients had no way to know a cookie was required and `apps/sip/pipeline/client.py`
    went on sending a bearer token the server ignores.
    """
    schemes = app.openapi()["components"]["securitySchemes"]
    assert schemes["SessionCookie"] == {
        "type": "apiKey",
        "in": "cookie",
        "name": SESSION_COOKIE,
        "description": schemes["SessionCookie"]["description"],
    }
    assert schemes["CsrfToken"]["in"] == "header"
    assert schemes["CsrfToken"]["name"] == CSRF_HEADER


@pytest.mark.parametrize(
    ("method", "path"),
    [(m, p) for m, p in business_routes() if m in {"POST", "PUT", "PATCH", "DELETE"}],
    ids=[f"{m} {p}" for m, p in business_routes() if m in {"POST", "PUT", "PATCH", "DELETE"}],
)
def test_write_routes_require_both_schemes_not_either(method: str, path: str) -> None:
    """A list of security requirements is OR in OpenAPI; one object with both keys is AND.

    FastAPI emits one entry per dependency, which published `[{cookie}, {csrf}]` and told every
    client that whichever it had would do. The server requires both, so the contract was
    describing an API more permissive than the one that exists.
    """
    operation = app.openapi()["paths"][path][method.lower()]
    security = operation["security"]
    assert len(security) == 1, f"{method} {path} publishes alternatives, not a conjunction"
    assert set(security[0]) == {"SessionCookie", "CsrfToken"}


@pytest.mark.parametrize(
    ("method", "path"),
    business_routes(),
    ids=[f"{m} {p}" for m, p in business_routes()],
)
def test_every_business_route_documents_refusal(method: str, path: str) -> None:
    """401 and 403 are the two outcomes an unauthenticated or under-privileged caller sees most
    often. A contract advertising only 200 and 422 gives a generated client no reason to handle
    either."""
    responses = app.openapi()["paths"][path][method.lower()]["responses"]
    assert "401" in responses and "403" in responses, (
        f"{method} {path} does not document 401/403; attach AUTH_RESPONSES to its router."
    )
