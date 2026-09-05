"""Session lifecycle against a real Postgres (#42).

Skipped without `DATABASE_URL`, same as the decision and persistence suites: the behaviour under
test here is expiry, the allowlist and immediate revocation, and a mock would only prove the mock
does what it was told. The rules that need no database are in `test_auth.py`.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import psycopg.rows
import pytest

from services.api.auth import (
    ABSOLUTE_LIFETIME,
    IDLE_TIMEOUT,
    AuthenticationError,
    NotAuthorisedError,
    SessionRepository,
    storage_id,
)
from services.api.tests.role_seed import role_id

DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set - session tests need a real Postgres with schema.sql applied",
)

# `roles.name` is unique and migration 0003 now pre-seeds ids 1-7 by name (#360). Picking an id
# nobody else claims stopped working the day that migration shipped: 'Reviewer' lives at whatever
# id migration 0003 gave it, so a literal `insert (3, 'Reviewer') on conflict do nothing` either
# no-ops against that existing row (leaving `user_roles` pointing at id 3's real name, whatever it
# is) or, worse, silently hands 'Reviewer' to an id already claimed by another seeded role.
# Resolved by name through `role_id()` instead - the same fix `_sip_owner_role` already needed in
# test_decisions.py.
REVIEWER_ROLE = "Reviewer"


@pytest.fixture
def repo() -> SessionRepository:
    return SessionRepository(DATABASE_URL)


def _make_user(*, active: bool = True, github_login: str | None = None, role: str | None = None) -> dict:
    """Seeded directly rather than through app code, so these tests do not inherit another
    module's bugs."""
    login = github_login or f"gh-{uuid.uuid4().hex[:12]}"
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        user = conn.execute(
            "insert into users (name, email, github_login, active) "
            "values (%s, %s, %s, %s) returning id",
            (f"User {uuid.uuid4()}", f"{uuid.uuid4()}@example.test", login, active),
        ).fetchone()
        if role is not None:
            role_pk = role_id(conn, role)
            conn.execute(
                "insert into user_roles (user_id, role_id) values (%s, %s)",
                (user["id"], role_pk),
            )
        conn.commit()
    return {"id": str(user["id"]), "github_login": login}


def test_a_known_active_login_gets_a_session(repo: SessionRepository) -> None:
    user = _make_user()
    principal = repo.establish_session(user["github_login"])
    assert principal.user_id == user["id"]
    assert principal.session_id
    assert principal.csrf_token


def test_an_unknown_github_login_is_refused(repo: SessionRepository) -> None:
    """The allowlist. Authenticating with GitHub says nothing about being an INZBC user."""
    with pytest.raises(NotAuthorisedError):
        repo.establish_session(f"stranger-{uuid.uuid4().hex[:8]}")


def test_an_inactive_user_is_refused(repo: SessionRepository) -> None:
    user = _make_user(active=False)
    with pytest.raises(NotAuthorisedError):
        repo.establish_session(user["github_login"])


def test_the_session_id_and_csrf_token_differ(repo: SessionRepository) -> None:
    """Double-submit only works if knowing the cookie does not give you the token."""
    principal = repo.establish_session(_make_user()["github_login"])
    assert principal.session_id != principal.csrf_token


def test_two_sessions_never_share_an_id(repo: SessionRepository) -> None:
    user = _make_user()
    first = repo.establish_session(user["github_login"])
    second = repo.establish_session(user["github_login"])
    assert first.session_id != second.session_id


def test_roles_come_from_user_roles(repo: SessionRepository) -> None:
    user = _make_user(role=REVIEWER_ROLE)
    assert repo.establish_session(user["github_login"]).has_role("Reviewer")


def test_a_disabled_role_grants_nothing(repo: SessionRepository) -> None:
    """`user_roles.enabled` exists so a role can be withdrawn without deleting the history."""
    user = _make_user(role=REVIEWER_ROLE)
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "update user_roles set enabled = false where user_id = %s", (user["id"],)
        )
        conn.commit()
    assert not repo.establish_session(user["github_login"]).has_role("Reviewer")


def test_a_valid_session_resolves(repo: SessionRepository) -> None:
    user = _make_user()
    session_id = repo.establish_session(user["github_login"]).session_id
    assert repo.resolve(session_id).user_id == user["id"]


def test_an_unknown_session_is_refused(repo: SessionRepository) -> None:
    with pytest.raises(AuthenticationError):
        repo.resolve("not-a-real-session-id")


def test_an_expired_session_is_refused_and_destroyed(repo: SessionRepository) -> None:
    """Absolute 12-hour lifetime, per ADR-0004. Destroyed rather than merely refused, so a clock
    change cannot revive it."""
    user = _make_user()
    session_id = repo.establish_session(user["github_login"]).session_id
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "update sessions set expires_at = %s where id = %s",
            (datetime.now(UTC) - timedelta(seconds=1), storage_id(session_id)),
        )
        conn.commit()

    with pytest.raises(AuthenticationError):
        repo.resolve(session_id)
    with psycopg.connect(DATABASE_URL) as conn:
        assert conn.execute(
            "select count(*) from sessions where id = %s", (storage_id(session_id),)
        ).fetchone()[0] == 0


def test_an_idle_session_is_refused(repo: SessionRepository) -> None:
    """60-minute idle timeout, separate from the absolute lifetime: an unattended session closes
    itself long before the 12 hours are up."""
    user = _make_user()
    session_id = repo.establish_session(user["github_login"]).session_id
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "update sessions set last_seen_at = %s where id = %s",
            (datetime.now(UTC) - timedelta(hours=2), storage_id(session_id)),
        )
        conn.commit()

    with pytest.raises(AuthenticationError):
        repo.resolve(session_id)


def test_activity_extends_the_idle_window_but_not_the_absolute_one(
    repo: SessionRepository,
) -> None:
    user = _make_user()
    principal = repo.establish_session(user["github_login"])
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        before = conn.execute(
            "select last_seen_at, expires_at from sessions where id = %s",
            (storage_id(principal.session_id),),
        ).fetchone()
        conn.execute(
            "update sessions set last_seen_at = %s where id = %s",
            (datetime.now(UTC) - timedelta(minutes=30), storage_id(principal.session_id)),
        )
        conn.commit()

    repo.resolve(principal.session_id)

    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        after = conn.execute(
            "select last_seen_at, expires_at from sessions where id = %s",
            (storage_id(principal.session_id),),
        ).fetchone()
    assert after["last_seen_at"] > datetime.now(UTC) - timedelta(minutes=1)
    assert after["expires_at"] == before["expires_at"]


def test_deactivating_a_user_ends_an_existing_session(repo: SessionRepository) -> None:
    """Offboarding takes effect on the next request, with no session cleanup and no deploy.
    This is the reason ADR-0004 chose server-side sessions over JWTs."""
    user = _make_user()
    session_id = repo.establish_session(user["github_login"]).session_id
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("update users set active = false where id = %s", (user["id"],))
        conn.commit()

    with pytest.raises(NotAuthorisedError):
        repo.resolve(session_id)


def test_a_role_withdrawn_mid_session_stops_applying(repo: SessionRepository) -> None:
    """Roles are re-read per request rather than frozen into the session at sign-in."""
    user = _make_user(role=REVIEWER_ROLE)
    session_id = repo.establish_session(user["github_login"]).session_id
    assert repo.resolve(session_id).has_role("Reviewer")

    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "update user_roles set enabled = false where user_id = %s", (user["id"],)
        )
        conn.commit()

    assert not repo.resolve(session_id).has_role("Reviewer")


def test_signing_out_ends_the_session(repo: SessionRepository) -> None:
    user = _make_user()
    session_id = repo.establish_session(user["github_login"]).session_id
    repo.end_session(session_id)
    with pytest.raises(AuthenticationError):
        repo.resolve(session_id)


def test_signing_in_records_the_login_time(repo: SessionRepository) -> None:
    user = _make_user()
    repo.establish_session(user["github_login"])
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        row = conn.execute(
            "select last_login_at from users where id = %s", (user["id"],)
        ).fetchone()
    assert row["last_login_at"] is not None


def test_the_absolute_lifetime_is_twelve_hours() -> None:
    """Named in ADR-0004. Asserted so a change to it is a deliberate edit here, not a silent one."""
    assert ABSOLUTE_LIFETIME == timedelta(hours=12)


def test_the_cookie_value_is_never_stored(repo: SessionRepository) -> None:
    """A leaked database must not hand over live sessions.

    Only the digest is written, so an attacker with a read-only snapshot, a backup or SQL access
    cannot copy `sessions.id`, send it as the cookie and act as that user. This asserts the
    property directly rather than trusting that every call site remembered to hash.
    """
    user = _make_user()
    principal = repo.establish_session(user["github_login"])
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        raw = conn.execute(
            "select count(*) from sessions where id = %s", (principal.session_id,)
        ).fetchone()
        hashed = conn.execute(
            "select count(*) from sessions where id = %s", (storage_id(principal.session_id),)
        ).fetchone()
    assert raw["count"] == 0, "the raw cookie value must never appear in the sessions table"
    assert hashed["count"] == 1


def _session_rows(session_id: str) -> int:
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        return conn.execute(
            "select count(*) from sessions where id = %s", (storage_id(session_id),)
        ).fetchone()["count"]


def test_an_idle_session_is_destroyed_not_just_refused(repo: SessionRepository) -> None:
    """Refusing and deleting are different guarantees, and only one was actually happening.

    The delete used to sit inside the same transaction as the raise, so the exception rolled it
    back: every expiry path refused the call and left the row in place. Asserting the row is gone
    is what catches that; asserting only the exception does not.
    """
    user = _make_user()
    session_id = repo.establish_session(user["github_login"]).session_id
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            "update sessions set last_seen_at = %s where id = %s",
            (datetime.now(UTC) - timedelta(hours=2), storage_id(session_id)),
        )
        conn.commit()

    with pytest.raises(AuthenticationError):
        repo.resolve(session_id)
    assert _session_rows(session_id) == 0


def test_a_deactivated_account_has_its_session_destroyed(repo: SessionRepository) -> None:
    """Otherwise re-activating the account silently revives whatever session was open."""
    user = _make_user()
    session_id = repo.establish_session(user["github_login"]).session_id
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("update users set active = false where id = %s", (user["id"],))
        conn.commit()

    with pytest.raises(NotAuthorisedError):
        repo.resolve(session_id)
    assert _session_rows(session_id) == 0


def _age_session(session_id: str, *, expires_at: datetime | None = None,
                 last_seen_at: datetime | None = None) -> None:
    """Backdates a session row, so expiry can be tested without waiting twelve hours."""
    with psycopg.connect(DATABASE_URL) as conn:
        if expires_at is not None:
            conn.execute(
                "update sessions set expires_at = %s where id = %s",
                (expires_at, storage_id(session_id)),
            )
        if last_seen_at is not None:
            conn.execute(
                "update sessions set last_seen_at = %s where id = %s",
                (last_seen_at, storage_id(session_id)),
            )
        conn.commit()


# `purge_expired` was written and left with no caller and no test. It is a bare DELETE with two
# boundary conditions, which is the shape of code that silently does the wrong thing: too eager
# and it signs out live users, too lax and expired rows accumulate personal data past their
# purpose. The tests below assert on *named rows* rather than on the return count, because the
# table is shared with every other session test and any count is whatever those left behind.


def test_purge_removes_a_session_past_its_absolute_expiry(repo: SessionRepository) -> None:
    session_id = repo.establish_session(_make_user()["github_login"]).session_id
    _age_session(session_id, expires_at=datetime.now(UTC) - timedelta(minutes=1))

    repo.purge_expired()

    assert _session_rows(session_id) == 0


def test_purge_removes_a_session_idle_past_the_timeout(repo: SessionRepository) -> None:
    """Idle and absolute expiry are separate conditions; a row can hit either one first."""
    session_id = repo.establish_session(_make_user()["github_login"]).session_id
    _age_session(session_id, last_seen_at=datetime.now(UTC) - IDLE_TIMEOUT - timedelta(minutes=1))

    repo.purge_expired()

    assert _session_rows(session_id) == 0


def test_purge_leaves_a_live_session_alone(repo: SessionRepository) -> None:
    """The failure that would actually hurt. A purge one boundary too wide signs out everyone
    currently working, and the two expiry tests above would still pass."""
    session_id = repo.establish_session(_make_user()["github_login"]).session_id

    repo.purge_expired()

    assert _session_rows(session_id) == 1
    assert repo.resolve(session_id).session_id == session_id


def test_purge_reports_how_many_it_removed(repo: SessionRepository) -> None:
    """Whatever else is in the table, purging two expired rows accounts for at least two."""
    first = repo.establish_session(_make_user()["github_login"]).session_id
    second = repo.establish_session(_make_user()["github_login"]).session_id
    for session_id in (first, second):
        _age_session(session_id, expires_at=datetime.now(UTC) - timedelta(minutes=1))

    assert repo.purge_expired() >= 2
