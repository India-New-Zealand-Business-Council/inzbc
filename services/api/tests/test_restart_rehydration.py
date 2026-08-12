"""Backend restart and rehydration integration test (#130).

Not a browser test - the server-side counterpart to the Playwright persistence test. Proves a
`runs` row's state survives a full **process** restart, not just a fresh request within the same
process: `RunRepository` and `CandidateRepository` hold no in-process cache (every method opens
its own `psycopg` connection and closes it - see `persistence.py`'s module docstring), so if state
were ever wrong after a restart, that would mean Postgres itself lost the write, not that some
in-memory dict needed clearing. This test proves the durability claim by actually killing the
`uvicorn` process and starting a new one, rather than trusting the "no in-process state" reasoning
on paper.

Skipped without `DATABASE_URL`, same convention as `test_persistence.py` - a real Postgres is the
whole point; nothing here would be worth proving against a mock.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator

import psycopg
import pytest
import requests

from services.api.auth import Principal, SessionRepository
from services.api.tests.role_seed import grant

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - restart/rehydration test needs a real Postgres with "
    "schema.sql applied",
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
_HEALTH_TIMEOUT_S = 10.0
_SHUTDOWN_TIMEOUT_S = 5.0


def _free_port() -> int:
    # Bind to port 0 and read back what the OS assigned, then release it. A race is possible
    # (something else could grab the port before uvicorn binds it a moment later) but is not
    # worth guarding against for a local/CI test process.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_server(port: int) -> subprocess.Popen:
    env = {**os.environ, "DATABASE_URL": DATABASE_URL}
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "services.api.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning",
        ],
        cwd=_REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.monotonic() + _HEALTH_TIMEOUT_S
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"server exited early (code {proc.returncode}):\n{proc.stdout.read()}"
            )
        try:
            response = requests.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
            if response.status_code == 200:
                return proc
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.1)
    proc.kill()
    raise TimeoutError(f"server did not become healthy within {_HEALTH_TIMEOUT_S}s")


def _stop_server(proc: subprocess.Popen) -> None:
    """SIGTERM first (uvicorn's graceful shutdown), SIGKILL if it doesn't exit - a hung process
    left behind would silently break every later test that tries to bind the same port range.
    """
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=_SHUTDOWN_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=_SHUTDOWN_TIMEOUT_S)


@pytest.fixture
def session() -> Principal:
    """A real user and a real session.

    This test drives a live uvicorn process over HTTP, so FastAPI's dependency overrides do not
    reach it: every request goes through the real authentication path (#42). That makes it the
    only test here that proves the whole chain end to end, and it means the caller needs an
    actual session rather than a caller-supplied actor id.
    """
    login = f"restart-{uuid.uuid4().hex[:12]}"
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "insert into users (name, email, github_login) values (%s, %s, %s) returning id",
            (f"Test User {uuid.uuid4()}", f"{uuid.uuid4()}@example.com", login),
        ).fetchone()
        # Analyst to create the run, SIP Owner to authorise it: `start` is launch authority and
        # is deliberately restricted to the owner. Seeded by name, so this does not depend on
        # which id another suite happened to claim first.
        grant(conn, row[0], "Analyst", "SIP Owner")
        conn.commit()
    return SessionRepository(DATABASE_URL).establish_session(login)


@pytest.fixture
def server_port() -> Iterator[int]:
    """Yields a free port; the test starts and stops its own server instances on it so it
    controls exactly when the restart happens, rather than sharing a session-scoped server.
    """
    yield _free_port()


def test_run_state_survives_a_full_process_restart(
    server_port: int, session: Principal
) -> None:
    proc = _start_server(server_port)
    base_url = f"http://127.0.0.1:{server_port}"
    # The session cookie authenticates; the CSRF header is required on every write.
    cookies = {"inzbc_session": session.session_id}
    headers = {"X-CSRF-Token": session.csrf_token}
    try:
        created = requests.post(
            f"{base_url}/api/runs",
            json={
                "run_number": f"RUN-RESTART-TEST-{uuid.uuid4().hex[:8]}",
                "prompt_version": "SIP-050 v1.1",
                "coverage_start_utc": "2026-07-27T07:00:00+12:00",
                "coverage_end_utc": "2026-07-28T07:00:00+12:00",
            },
            cookies=cookies,
            headers=headers,
            timeout=5,
        ).json()
        assert created["state"] == "Draft"

        transitioned = requests.post(
            f"{base_url}/api/runs/{created['id']}/start",
            json={
                "expected_version": 0,
                "reason": "authorise run",
                "approval_ref": "launch-authority-recorded",
            },
            cookies=cookies,
            headers=headers,
            timeout=5,
        ).json()
        assert transitioned["state"] == "Run Authorised"
        assert transitioned["version"] == 1
    finally:
        _stop_server(proc)

    # A fresh OS process, same port, no code path shared with the one above - if anything in the
    # previous process's memory (rather than Postgres) had been the actual source of truth, this
    # process would come up with no knowledge of the run at all.
    proc2 = _start_server(server_port)
    try:
        rehydrated = requests.get(
            f"{base_url}/api/runs/{created['id']}", cookies=cookies, timeout=5
        ).json()
    finally:
        _stop_server(proc2)

    assert rehydrated["state"] == "Run Authorised"
    assert rehydrated["version"] == 1
    assert rehydrated["run_number"] == created["run_number"]
    assert rehydrated["id"] == created["id"]
