"""Session-wide pytest configuration.

`services/api/hardening.py` installs a rate limiter (60 requests/60s by default, shared across the
whole process because `services.api.main.app` is a module-level singleton every test file
imports). That's the right default for production, but it makes the *test suite's own* request
count meaningful: `pyproject.toml` runs every test under `apps`/`services` in one pytest session
(`testpaths = ["apps", "services"]`), so every `TestClient` request across every file that ever
imports `main.app` shares one counter. Enough HTTP-hitting test files in the same run pushes the
total past 60 and later tests start seeing 429s that have nothing to do with what they're testing
- discovered while adding `services/api/tests/test_comms_api.py`, which was enough on its own to
tip `test_runs_api.py`'s later tests over the limit.

Raising the limit via `RATE_LIMIT_REQUESTS`, the environment variable `hardening.py` already reads
and documents, rather than changing anything in that module: this is test configuration, not a
change to the control itself, and it must be set before `services.api.main` is imported by any
test module (a root `conftest.py` is collected before test files, so this runs first). Set only if
a caller (e.g. CI) hasn't already chosen a value.
"""

import os

import pytest

os.environ.setdefault("RATE_LIMIT_REQUESTS", "100000")


# The API routers now require an authenticated session (#42). Every router test that predates
# that change drives `services.api.main.app` directly and would otherwise get 401 on every
# request, testing nothing but the auth dependency it is not there to test.
#
# This fixture supplies a fixed principal to those tests so each keeps testing what it was
# written for. It deliberately does NOT prove the routes are protected: that would be circular,
# since the fixture is what makes them pass. `services/api/tests/test_router_auth.py` asserts the
# protection separately, against an app with no overrides.
@pytest.fixture(autouse=True)
def _authenticated_principal():
    from services.api.auth import Principal
    from services.api.main import app
    from services.api.session import require_csrf, require_principal

    principal = Principal(
        user_id="00000000-0000-0000-0000-0000000000aa",
        name="Test Principal",
        roles=frozenset({"SIP Owner", "Analyst", "Reviewer"}),
        session_id="test-session",
        csrf_token="test-csrf",
    )
    app.dependency_overrides[require_principal] = lambda: principal
    app.dependency_overrides[require_csrf] = lambda: principal
    yield principal
    app.dependency_overrides.pop(require_principal, None)
    app.dependency_overrides.pop(require_csrf, None)
