"""Hardening for the public API surface (#98).

The FTA endpoint is unauthenticated, public, and about to be deployed. That combination is the
whole reason this module exists: anything reachable without a credential is reachable by anyone,
including automated traffic that has no interest in tariffs.

Four concerns, deliberately kept in one small module rather than spread across the app:

1. **A consistent error envelope.** FastAPI's default is `{"detail": ...}`, which differs in shape
   between a validation failure and a raised `HTTPException`, and an unhandled exception returns a
   plain-text 500. A caller cannot branch on that reliably, and an unhandled exception should never
   put an internal message on the wire.

2. **Rate limiting.** See `RateLimiter` for what this does and does not protect against.

3. **Security headers.** Cheap, static, and they close off whole classes of problem before they
   start.

4. **CORS, off unless configured.** ADR-0004 enables CORS only on the public read endpoint, and
   only once the two front ends are split across hosts. Today the image serves both from one
   origin (`Dockerfile`), so CORS is not needed and is not enabled. The configuration exists so
   that when the split happens it is a deployment variable rather than a code change, and it
   defaults to nothing: an unset variable allows no origins rather than all of them.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Requests per window, per client. Generous for a human reading tariff answers and low enough that
# a scraper has to slow down. Overridable so a deployment can tighten without a release.
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

# Paths that must answer even when a client is being rate limited, or the host will conclude the
# instance is unhealthy and restart it in the middle of the traffic that triggered the limit.
_EXEMPT_PATHS = frozenset({"/health"})

# Only sweep expired clients once the map is big enough to be worth walking.
_SWEEP_AT = 1024


def error_body(status: int, code: str, message: str) -> dict:
    """The one error shape every failure uses.

    `code` is a stable machine-readable string; `message` is for a human. Nothing else is
    included, because an error body is the easiest place to leak an internal detail by accident.
    """
    return {"error": {"status": status, "code": code, "message": message}}


class RateLimiter:
    """Fixed-window request counting, per client, held in memory.

    ponytail: in-memory and per-instance. On a host that scales to N instances the effective limit
    is N times the configured one, and a restart forgets every counter. That is a real ceiling and
    it is stated rather than discovered later. It is still worth having: it stops a single client
    hammering one instance, which is the realistic case for a small public endpoint. The upgrade
    path, when there is a reason to take it, is a shared counter in Redis or the database.

    Deliberately not protection against a distributed attack. Nothing at this layer is. That is the
    host's job, and ADR-0004 puts this behind a managed platform for exactly that reason.
    """

    def __init__(self, limit: int = RATE_LIMIT_REQUESTS, window: int = RATE_LIMIT_WINDOW_SECONDS):
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, client: str, now: float | None = None) -> bool:
        """True if this request is allowed. Records it when it is."""
        now = time.monotonic() if now is None else now
        hits = self._hits[client]
        cutoff = now - self.window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        # An entry is only kept for a request that is allowed. Counting refused requests too would
        # let a client that is already over the limit hold itself over it indefinitely.
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        if len(self._hits) > _SWEEP_AT:
            self._sweep(cutoff)
        return True

    def _sweep(self, cutoff: float) -> None:
        """Drop clients with nothing left in the window.

        Without this, one entry is retained per address ever seen, so a long-running instance
        facing many distinct clients grows without bound. Only runs once the map is large enough
        to be worth walking.
        """
        for client in [c for c, h in self._hits.items() if not h or h[-1] <= cutoff]:
            del self._hits[client]


def _client_key(request: Request) -> str:
    """Identify the caller for rate limiting.

    Uses the socket address, not `X-Forwarded-For`. A forwarded header is caller-supplied, so
    trusting it lets anyone reset their own limit by changing one header. When this runs behind a
    proxy that rewrites the socket address, the proxy's own forwarded handling is the place to fix
    that, not here.
    """
    return request.client.host if request.client else "unknown"


def install(app: FastAPI, limiter: RateLimiter | None = None) -> FastAPI:
    """Adds the error envelope, rate limiting, security headers and optional CORS to `app`."""
    limiter = limiter or RateLimiter()

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.status_code, "http_error", str(exc.detail)),
            headers=getattr(exc, "headers", None) or {},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # The field and reason are safe to return and are what a caller needs to fix the request.
        # The submitted input is not echoed: a rejected value can be exactly the thing that should
        # not be written into a log or bounced back through a browser.
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", ()) if p != "query") or "request"
        return JSONResponse(
            status_code=422,
            content=error_body(422, "invalid_request",
                               f"{where}: {first.get('msg', 'failed validation')}"),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, _exc: Exception) -> JSONResponse:
        # Never the exception text. An unhandled error is exactly where a stack detail, a query or
        # a connection string reaches a stranger.
        return JSONResponse(
            status_code=500,
            content=error_body(500, "internal_error", "The request could not be completed."),
        )

    @app.middleware("http")
    async def _limit_and_headers(request: Request, call_next):
        if request.url.path not in _EXEMPT_PATHS and not limiter.check(_client_key(request)):
            response = JSONResponse(
                status_code=429,
                content=error_body(429, "rate_limited",
                                   "Too many requests. Try again shortly."),
                headers={"Retry-After": str(limiter.window)},
            )
        else:
            response = await call_next(request)

        # Static, cheap, and they apply to the served UI as much as to the API.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response

    # Empty and absent both mean no cross-origin access. Fail closed: a deployment that forgets to
    # set this gets a working same-origin service, not an open one.
    origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,  # public read endpoint; no cookies cross an origin
            allow_methods=["GET"],
            allow_headers=["Content-Type"],
        )
    return app
