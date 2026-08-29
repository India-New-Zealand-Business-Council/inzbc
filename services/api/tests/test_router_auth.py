"""Every business route requires a session (#42).

**Why this file exists separately.** The root `conftest.py` installs an autouse fixture that
supplies a principal to `services.api.main.app`, so the router tests written before #42 keep
testing what they were written for instead of returning 401 everywhere. That fixture is also
exactly what would hide a route someone forgot to protect.

So this file opts out of the override and drives the real app. If a route is added without an
auth dependency, or an existing one loses it, the enumeration below fails.

The exploit this closes, found in adversarial review: an anonymous caller reads `GET /api/runs`,
which returns run ids and a valid `initiated_by` user UUID, then posts that UUID as `actor_id` to
`POST /api/runs/{id}/start` with any non-empty `approval_ref`, and the audit trail records the
impersonated user as having authorised the run. The launch gate accepted unverifiable free text at
the time; it now checks `run_authorisations` (#227), so both halves of that exploit are closed
rather than one.
"""

from __future__ import annotations

import sys
from pathlib import Path

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
REPO_ROOT = Path(__file__).resolve().parents[3]

SESSION_PREFIX = "/api/session"

# The sign-in handshake itself. `/api/auth/github` and its callback are how an anonymous caller
# becomes an authenticated one, so requiring a session to reach them would be circular. They are
# not unprotected: the callback is guarded by the OAuth `state` cookie against handshake CSRF,
# and by the allowlist in `establish_session`. Covered by `test_oauth.py`.
OAUTH_PREFIX = "/api/auth"


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
        if route.path.startswith(
            (*PUBLIC_PREFIXES, SESSION_PREFIX, OAUTH_PREFIX)
        ):
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


# The authority each route carries, stated once so a change has to be made deliberately in two
# places. The general test above catches a route with no authority at all, which was the #278
# defect; it cannot catch a *wrong* authority, because it only asks whether some recognised role
# is named. Moving `/verify` to Auditor, or opening a sensitive write to every staff role, would
# satisfy it. This map is what makes that fail.
#
# Sourced from the requirements, not from the implementation: docs/requirements.md for the
# Analyst capture and scoring stories and the Quality Reviewer verification story, REQ-U-01 and
# REQ-U-02 for the QA failure and CEO decision split, and launch-config.md for the Secretariat
# distribution owner.
EXPECTED_ROLES: dict[tuple[str, str], set[str]] = {
    ("POST", "/api/runs"): {"Analyst", "SIP Owner"},
    ("GET", "/api/runs"): set(STAFF_READ),
    ("GET", "/api/runs/{run_id}"): set(STAFF_READ),
    # Every staff role, and deliberately so: the Auditor and Board Viewer roles exist to read
    # this. Restricting it to the owner would let the person most likely to be audited decide
    # who sees the record.
    ("GET", "/api/runs/{run_id}/audit"): set(STAFF_READ),
    # Launch, CEO and resumption authority. Owner only.
    ("POST", "/api/runs/{run_id}/start"): {"SIP Owner"},
    ("POST", "/api/runs/{run_id}/pause"): {"SIP Owner"},
    ("POST", "/api/runs/{run_id}/resume"): {"SIP Owner"},
    ("POST", "/api/runs/{run_id}/stop"): {"SIP Owner"},
    # REQ-U-01: the reviewer's independent stop. Deliberately not the owner's alone.
    ("POST", "/api/runs/{run_id}/fail-qa"): {"Reviewer", "SIP Owner"},
    ("POST", "/api/runs/{run_id}/complete"): {"Analyst", "SIP Owner"},
    ("POST", "/api/candidates"): {"Analyst", "SIP Owner"},
    ("GET", "/api/candidates"): set(STAFF_READ),
    ("GET", "/api/candidates/{candidate_id}"): set(STAFF_READ),
    ("POST", "/api/candidates/{candidate_id}/score"): {"Analyst", "SIP Owner"},
    ("POST", "/api/candidates/{candidate_id}/route"): {"Analyst", "SIP Owner"},
    ("POST", "/api/candidates/{candidate_id}/merge"): {"Analyst", "SIP Owner"},
    # The reviewer's job. BR8 additionally refuses whoever captured or assessed it.
    ("POST", "/api/candidates/{candidate_id}/verify"): {"Reviewer", "SIP Owner"},
    # Spends money per call, so narrower than the other writes.
    ("POST", "/api/comms/draft"): {"Secretariat", "SIP Owner"},
    # Every staff role. A dashboard the board cannot open is not an executive dashboard.
    ("GET", "/api/dashboard"): set(STAFF_READ),
    # Drafting the report is the analyst's act; the owner may also submit.
    ("POST", "/api/reports"): {"Analyst", "SIP Owner"},
    # A decision record only its decider can read is not evidence anyone else can rely on.
    ("GET", "/api/reports/{report_version_id}"): set(STAFF_READ),
    # SIP-188 QA result. Reviewer or SIP Owner may record one; the repository separately refuses
    # the analyst on that particular run, the same two-gate split as candidates/{id}/verify.
    # Analyst is absent on purpose: QA is the check on the analyst's work.
    ("POST", "/api/reports/{report_version_id}/qa"): {"Reviewer", "SIP Owner"},
    # The three decision streams (ADR-0005). Each carries the roles its own decision kind is
    # granted to in database/migrations/0003, not one shared set: the HTTP gate and the
    # decision_role_permissions grant have to agree, or a caller passes the route check and is
    # then refused by the repository, which reads as a bug rather than as the control working.
    #
    # Ruling is the CEO's alone. Approval reaches Reviewer because a quality judgement only the
    # owner can make is not independent of the owner. Distribution reaches Secretariat because
    # sending is a secretariat act, and it stays a separate decision from approval per REQ-G-04.
    ("POST", "/api/reports/{report_version_id}/ruling"): {"SIP Owner"},
    ("POST", "/api/reports/{report_version_id}/approval"): {"Reviewer", "SIP Owner"},
    ("POST", "/api/reports/{report_version_id}/distribution"): {"Secretariat", "SIP Owner"},
    # The SIP-185 mandatory-source register. Reference data every role needs to read to know
    # which sources a run was obliged to cover; nothing personal in it and no write path here,
    # but it is the register an auditor checks a run against, so it is not public either.
    ("GET", "/api/source-library"): set(STAFF_READ),
    # SIP-184 step 4: recording whether a mandatory source was covered for a run. Same authority
    # as capture (`POST /api/candidates`) because it is the same act — the analyst working the
    # run states what they found. Deliberately not the Reviewer's: the outcome per source is
    # evidence to be verified, not the verification.
    ("POST", "/api/runs/{run_id}/source-checks"): {"Analyst", "SIP Owner"},
    # Read side of the same record, and the Auditor's view of coverage. Same reasoning as
    # `/api/runs/{run_id}/audit`: restricting it to the role being audited defeats the point.
    ("GET", "/api/runs/{run_id}/source-checks"): set(STAFF_READ),
    # Registers (#209): operational trackers and the append-only exceptions log. Same authority
    # shape as source-checks - the analyst working the run records what they found; the register
    # is reference/evidence every staff role needs to read.
    ("POST", "/api/action-register"): {"Analyst", "SIP Owner"},
    ("POST", "/api/action-register/{action_id}/status"): {"Analyst", "SIP Owner"},
    ("GET", "/api/action-register/{action_id}"): set(STAFF_READ),
    ("GET", "/api/action-register"): set(STAFF_READ),
    ("POST", "/api/watch-lists"): {"Analyst", "SIP Owner"},
    ("POST", "/api/watch-lists/{watch_id}/status"): {"Analyst", "SIP Owner"},
    ("GET", "/api/watch-lists/{watch_id}"): set(STAFF_READ),
    ("GET", "/api/watch-lists"): set(STAFF_READ),
    ("POST", "/api/exceptions"): {"Analyst", "SIP Owner"},
    # Inserts a new row rather than editing the one named in the path (append-only), but it is
    # still the analyst's act of recording what they found, same authority as the write above.
    ("POST", "/api/exceptions/{exception_id}/correct"): {"Analyst", "SIP Owner"},
    ("GET", "/api/exceptions/{exception_id}"): set(STAFF_READ),
    ("GET", "/api/exceptions"): set(STAFF_READ),
    # Approved facts library (#188): drafting is capture (Analyst), approving is verification and
    # must be a different actor than the drafter - Reviewer or SIP Owner, never Analyst alone.
    # Archiving retires a claim rather than asserting one, so any writer role may do it.
    ("POST", "/api/facts"): {"Analyst", "SIP Owner"},
    ("POST", "/api/facts/{fact_id}/approve"): {"Reviewer", "SIP Owner"},
    ("POST", "/api/facts/{fact_id}/archive"): {"Analyst", "Reviewer", "SIP Owner"},
    ("GET", "/api/facts/{fact_id}"): set(STAFF_READ),
    ("GET", "/api/facts/by-key/{fact_key}/latest"): set(STAFF_READ),
    ("GET", "/api/facts/by-key/{fact_key}/history"): set(STAFF_READ),
    # The named-reviewer approval gate #60 depends on. BR8: refuse_self_review checks the author
    # against the approver regardless of role, so Reviewer/SIP Owner here is "may approve
    # something", not "may approve their own draft" - that second check lives in the repository,
    # not in the role map, the same split as /api/candidates/{id}/verify.
    ("POST", "/api/comms/drafts/{draft_id}/approve"): {"Reviewer", "SIP Owner"},
    # Deleting a draft (#342) takes the roles that can create one, not the reviewer roles that
    # approve. It is a privacy-erasure act: the person who typed a member's name into a brief is
    # the one who notices, and the audit record makes it attributable without restricting it to a
    # single person who may be unavailable.
    ("DELETE", "/api/comms/drafts/{draft_id}"): {"Secretariat", "SIP Owner"},
    ("GET", "/api/comms/drafts/{draft_id}"): set(STAFF_READ),
    ("GET", "/api/comms/drafts"): set(STAFF_READ),
}


def test_the_expected_role_map_covers_every_business_route() -> None:
    """Guards the map. A route added without an entry would otherwise be silently unchecked by
    the test below, which is the same failure mode as the original bug one level up."""
    actual = {(method, path) for method, path in business_routes()}
    missing = actual - set(EXPECTED_ROLES)
    extra = set(EXPECTED_ROLES) - actual
    assert not missing, f"routes with no expected-roles entry: {sorted(missing)}"
    assert not extra, f"expected-roles entries for routes that do not exist: {sorted(extra)}"


@pytest.mark.parametrize(
    ("method", "path"),
    business_routes(),
    ids=[f"{m} {p}" for m, p in business_routes()],
)
def test_every_route_carries_exactly_the_authority_it_should(method: str, path: str) -> None:
    """The check the general test cannot make: not "some role", but *which*.

    Widening a route to an extra role, or moving it to the wrong one, fails here. Changing who
    may do what then has to be a deliberate edit to `EXPECTED_ROLES` as well as to the route,
    which is the point: the map is a second opinion, not a mirror of the implementation.
    """
    route = next(r for r in _walk(app.routes) if r.path == path and method in r.methods)
    actual = _dependency_names(route) & set(ALL_ROLES)
    assert actual == EXPECTED_ROLES[(method, path)], (
        f"{method} {path} carries {sorted(actual)}, expected "
        f"{sorted(EXPECTED_ROLES[(method, path)])}. If this change is intended, update "
        f"EXPECTED_ROLES and say why in the pull request."
    )


def test_the_runtime_image_installs_everything_the_api_imports() -> None:
    """The Dockerfile hand-lists its dependencies, so it drifts silently.

    It installs a named set rather than the project, deliberately: installing the whole project
    would pull in the collector's dependencies, which this service does not run. The cost is that
    adding an import to `services/api/` does not add it to the image, and nothing notices until
    the container will not start.

    That is not hypothetical. `services/api/oauth.py` imported `httpx`, which was present locally
    as a test dependency and absent from the image, so every check passed except the container
    smoke test. This asserts the two agree.
    """
    import ast
    import re

    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    # Arrive as dependencies of a package the Dockerfile already installs, so naming them again
    # would be noise. `starlette` ships with fastapi.
    transitive = {"starlette", "click"}
    stdlib = set(sys.stdlib_module_names)

    # Module-level imports only. An import inside a function does not run at startup, so it
    # cannot stop the container: `model_gateway.py` imports `openai` lazily precisely so a
    # deployment with no model configured still serves the FTA path.
    imported: set[str] = set()
    for path in (REPO_ROOT / "services" / "api").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])

    third_party = {
        name for name in imported
        if name not in stdlib
        and name not in {"services", "apps", "__future__"}
        and name not in transitive
    }
    # Matched as a quoted requirement rather than a substring: a plain `in` check passes on
    # `"httpx-something-else"`, which is exactly the false negative that would let this test
    # report success while the container still fails.
    installed = set(re.findall(r'"([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?[><=!~]', dockerfile))
    missing = third_party - installed

    assert not missing, (
        f"{sorted(missing)} imported at module level by services/api and not installed in the "
        f"Dockerfile. The API will start locally and the container will not."
    )
