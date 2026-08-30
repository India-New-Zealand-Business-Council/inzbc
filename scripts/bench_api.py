"""Latency and concurrency baseline for the REST API (#335).

Drives a real uvicorn process over HTTP through the real authentication path, so the numbers
include session lookup, CSRF verification, role resolution and the audit write - not just the SQL.
An in-process TestClient would measure something the deployed system never does.

Reports p50 and p95 rather than a mean, because a mean hides the tail and the tail is what a user
notices.

    DATABASE_URL=postgresql://inzbc:inzbc@localhost:5432/inzbc_bench3 \
        .venv/Scripts/python.exe scripts/bench_api.py

Requires a database whose name contains `bench`, already carrying the schema. Seed volume first
with scripts/bench_indexes.py against the same database.
"""

from __future__ import annotations

import os
import socket
import statistics
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
import requests

from services.api.auth import SessionRepository
from services.api.tests.role_seed import authorise_run, grant

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = 60
# Boot budget for a cold subprocess importing the whole app. Measured at 7.3-8.3s idle on this
# machine, so 45s leaves room under load - same reasoning as _HEALTH_TIMEOUT_S in
# services/api/tests/test_restart_rehydration.py.
HEALTH_TIMEOUT_S = 45.0


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_server(port: int, database_url: str) -> subprocess.Popen:
    # The API rate-limits at 60 requests per 60 seconds per client (services/api/hardening.py).
    # A latency benchmark sends far more than that, so without raising the ceiling here every
    # endpoint after the first returns 429 and the run measures the rate limiter instead of the
    # endpoint - which is what the first attempt at this script actually did.
    #
    # Raised only for the benchmark process. The default is deliberate and stays the default; the
    # limiter's own behaviour is verified by its tests, not here.
    env = {
        **os.environ,
        "DATABASE_URL": database_url,
        "RATE_LIMIT_REQUESTS": "100000",
        "RATE_LIMIT_WINDOW_SECONDS": "60",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "services.api.main:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=REPO_ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    deadline = time.monotonic() + HEALTH_TIMEOUT_S
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited early:\n{proc.stdout.read()}")
        try:
            if requests.get(f"http://127.0.0.1:{port}/health", timeout=2).status_code == 200:
                return proc
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            pass
        time.sleep(0.1)
    proc.kill()
    raise TimeoutError(f"server not healthy within {HEALTH_TIMEOUT_S}s")


def make_session(database_url: str, run_id: str) -> tuple:
    """Returns (principal, approval_ref).

    The approval_ref is a real `run_authorisations` row rather than a made-up string, because
    `apply_transition` checks it against that table - passing a plausible-looking string would
    document the gate while not exercising it.
    """
    login = f"bench-{uuid.uuid4().hex[:12]}"
    with psycopg.connect(database_url) as conn:
        row = conn.execute(
            "insert into users (name, email, github_login) values (%s, %s, %s) returning id",
            (f"Bench {uuid.uuid4()}", f"{uuid.uuid4()}@example.invalid", login),
        ).fetchone()
        actor_id = row[0]
        grant(conn, actor_id, "Analyst", "SIP Owner", "Quality Reviewer")
        approval_ref = authorise_run(conn, run_id, str(actor_id))
        conn.commit()
    return SessionRepository(database_url).establish_session(login), approval_ref


def percentiles(samples: list[float]) -> tuple[float, float]:
    ordered = sorted(samples)
    p50 = statistics.median(ordered)
    # Nearest-rank p95. With 60 samples that is the 57th, which is a real observation rather than
    # an interpolation between two - honest for a sample this size.
    p95 = ordered[min(len(ordered) - 1, round(0.95 * len(ordered)) - 1)]
    return p50 * 1000, p95 * 1000


def time_get(url: str, cookies: dict, n: int = SAMPLES) -> tuple[float, float, int]:
    times, status = [], 0
    for _ in range(n):
        t0 = time.perf_counter()
        r = requests.get(url, cookies=cookies, timeout=30)
        times.append(time.perf_counter() - t0)
        status = r.status_code
    p50, p95 = percentiles(times)
    return p50, p95, status


def concurrency_probe(base: str, cookies: dict, headers: dict, run_id: str,
                      version: int, approval_ref: str, workers: int = 8):
    """Fires parallel writes that all claim the same version, and reports what came back.

    This is the real test of the optimistic-concurrency path in services/api/persistence.py.
    Every worker sends the *same* `expected_version`, so exactly one may win: the first write
    advances the version, and every later write is then claiming a version that no longer exists.

    A conflict response here is the control working. The failure this detects is two workers both
    reporting 200 on the same expected_version, which would mean a lost update.

    `start` is the transition used because it is the one legal move out of Draft, which is the
    state seeded runs are in. It is human-gated, so `approval_ref` must name a real
    `run_authorisations` row - hence the caller passing one in.
    """
    def one(_):
        try:
            r = requests.post(
                f"{base}/api/runs/{run_id}/start",
                cookies=cookies, headers=headers,
                json={
                    "expected_version": version,
                    "reason": "bench concurrency probe",
                    "approval_ref": approval_ref,
                },
                timeout=30,
            )
            return r.status_code
        except Exception as exc:  # noqa: BLE001 - the status distribution is the result
            return type(exc).__name__

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, range(workers)))
    tally: dict = {}
    for r in results:
        tally[r] = tally.get(r, 0) + 1
    return tally


def main() -> int:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1
    if "bench" not in url:
        print(f"refusing: DATABASE_URL must name a bench database, got {url!r}", file=sys.stderr)
        return 1

    with psycopg.connect(url) as conn:
        counts = {
            t: conn.execute(f"select count(*) from {t}").fetchone()[0]
            for t in ("runs", "candidates", "audit_log")
        }
        row = conn.execute("select id, version from runs limit 1").fetchone()
        run_id = str(row[0]) if row else None
        run_version = int(row[1]) if row else 1
    if not run_id:
        print("no runs seeded - run scripts/bench_indexes.py against this database first",
              file=sys.stderr)
        return 1

    print(f"dataset: {counts}")
    print("note: benchmark process runs with the rate limit raised; production default is "
          "60 requests / 60 seconds per client")
    principal, approval_ref = make_session(url, run_id)
    cookies = {"inzbc_session": principal.session_id}
    headers = {"X-CSRF-Token": principal.csrf_token}

    port = free_port()
    proc = start_server(port, url)
    base = f"http://127.0.0.1:{port}"
    try:
        endpoints = [
            ("GET /health", f"{base}/health"),
            ("GET /api/runs", f"{base}/api/runs"),
            ("GET /api/runs/{id}", f"{base}/api/runs/{run_id}"),
            ("GET /api/candidates?run", f"{base}/api/candidates?run={run_id}"),
            ("GET /api/dashboard", f"{base}/api/dashboard"),
            ("GET /api/runs/{id}/audit", f"{base}/api/runs/{run_id}/audit"),
        ]
        print(f"\n{'endpoint':<30} {'p50':>9} {'p95':>9}   status  ({SAMPLES} samples)")
        print("-" * 70)
        for label, u in endpoints:
            p50, p95, status = time_get(u, cookies)
            print(f"{label:<30} {p50:>7.1f}ms {p95:>7.1f}ms   {status}")

        print(f"\nconcurrency probe - 8 parallel writes, all claiming version {run_version}:")
        for status, n in sorted(
            concurrency_probe(base, cookies, headers, run_id, run_version, approval_ref).items(),
            key=lambda kv: str(kv[0]),
        ):
            print(f"  {status}: {n}")
        print("  expected: exactly one 200, the rest refused as version conflicts")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
