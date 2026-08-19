"""The public surface is unauthenticated, so these are the controls standing in for a credential.

Each test names the thing that goes wrong without it, because a hardening test that only asserts a
header exists tells the next reader nothing about why it is there.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from services.api.hardening import RateLimiter, install


def _app(limiter: RateLimiter | None = None) -> FastAPI:
    app = FastAPI()

    @app.get("/ok")
    def ok() -> dict:
        return {"ok": True}

    @app.get("/boom")
    def boom() -> dict:
        raise RuntimeError("connection to db-prod-01 failed with password hunter2")

    @app.get("/teapot")
    def teapot() -> dict:
        raise HTTPException(status_code=418, detail="short and stout")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return install(app, limiter=limiter)


# --- the error envelope -----------------------------------------------------------------------


def test_an_unhandled_error_never_puts_its_message_on_the_wire():
    """The failure this exists for: an internal detail reaching a stranger.

    An unhandled exception is where a hostname, a query or a credential escapes, and this endpoint
    is public. The client gets a 500 and nothing else.
    """
    client = TestClient(_app(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    body = response.text
    assert "hunter2" not in body
    assert "db-prod-01" not in body
    assert response.json() == {
        "error": {"status": 500, "code": "internal_error",
                  "message": "The request could not be completed."}
    }


def test_every_failure_uses_the_same_shape():
    """FastAPI's default differs between a validation failure and a raised HTTPException.

    A caller cannot branch on a shape that changes with the kind of failure, so it ends up parsing
    whichever one it happened to see first.
    """
    client = TestClient(_app(), raise_server_exceptions=False)

    for path, status in [("/teapot", 418), ("/boom", 500), ("/nope", 404)]:
        body = client.get(path).json()
        assert set(body) == {"error"}, path
        assert set(body["error"]) == {"status", "code", "message"}, path
        assert body["error"]["status"] == status, path


def test_a_validation_failure_names_the_field_without_echoing_the_input(monkeypatch):
    """A rejected value is exactly the thing not to reflect back or write to a log."""
    from services.api.main import app as real_app

    client = TestClient(real_app, raise_server_exceptions=False)
    response = client.get("/api/fta/query", params={"q": "x" * 900})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_request"
    assert "q" in body["error"]["message"]
    assert "xxxx" not in response.text


# --- rate limiting ----------------------------------------------------------------------------


def test_a_client_over_the_limit_is_refused_with_a_retry_hint():
    client = TestClient(_app(RateLimiter(limit=3, window=60)))

    assert [client.get("/ok").status_code for _ in range(3)] == [200, 200, 200]

    refused = client.get("/ok")
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "rate_limited"
    assert refused.headers["Retry-After"] == "60"


def test_a_refused_request_does_not_extend_the_block():
    """Counting refusals would let a client that is already over the limit hold itself over it.

    Every retry would push the window forward, so a caller hammering the endpoint could never get
    back in even after going quiet.
    """
    limiter = RateLimiter(limit=2, window=10)

    assert limiter.check("a", now=0.0)
    assert limiter.check("a", now=1.0)
    assert not limiter.check("a", now=2.0)
    assert not limiter.check("a", now=3.0)

    # The two allowed hits, at 0.0 and 1.0, have left the window by 11.1. The refusals at 2.0 and
    # 3.0 were never recorded, so they cannot hold the door shut.
    assert limiter.check("a", now=11.1)


def test_one_client_hitting_the_limit_does_not_affect_another():
    limiter = RateLimiter(limit=1, window=60)

    assert limiter.check("first", now=0.0)
    assert not limiter.check("first", now=1.0)
    assert limiter.check("second", now=1.0)


def test_health_answers_even_when_the_caller_is_rate_limited():
    """Otherwise the host reads the instance as unhealthy and restarts it mid-incident, which is
    the worst possible moment to lose it."""
    client = TestClient(_app(RateLimiter(limit=1, window=60)))

    client.get("/ok")
    assert client.get("/ok").status_code == 429
    assert client.get("/health").status_code == 200


def test_expired_clients_are_swept_so_the_map_does_not_grow_forever():
    limiter = RateLimiter(limit=5, window=10)
    for i in range(1500):
        limiter.check(f"client-{i}", now=0.0)

    # Well past the window, so every earlier client is expired. The next call sweeps them.
    limiter.check("late", now=100.0)

    assert len(limiter._hits) < 1500


# --- headers and CORS -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "value"),
    [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ],
)
def test_security_headers_are_present(header, value):
    assert TestClient(_app()).get("/ok").headers[header] == value


def test_cors_is_off_unless_it_is_configured(monkeypatch):
    """Fail closed. A deployment that forgets the variable gets a working same-origin service, not
    an open one.

    ADR-0004 enables CORS only on the public read endpoint once the two front ends are split across
    hosts. Today the image serves both from one origin, so there is nothing to allow.
    """
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    client = TestClient(_app())

    response = client.get("/ok", headers={"Origin": "https://evil.test"})

    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


def test_cors_allows_only_the_configured_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://inzbc.org")
    client = TestClient(_app())

    allowed = client.get("/ok", headers={"Origin": "https://inzbc.org"})
    assert allowed.headers.get("access-control-allow-origin") == "https://inzbc.org"

    other = client.get("/ok", headers={"Origin": "https://evil.test"})
    assert other.headers.get("access-control-allow-origin") != "https://evil.test"
