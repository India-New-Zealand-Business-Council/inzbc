"""Session authentication and role authorisation (#42).

Implements the transport ADR-0004 specifies and every router so far has had to work without:
an opaque server-side session, an allowlist check against `users.github_login`, and role
checks that read `user_roles` rather than trusting anything the caller sends.

**Why this exists.** Until now `actor_id` arrived in the request body, caller-supplied. Every
audit row and every approval therefore recorded a *claim* about who acted, not an identity.
`database/schema.sql` says decision-level separation of duties is not enforced, and it could not
be: with an unauthenticated `actor_id` the same person can be analyst, reviewer and approver by
typing three different UUIDs. This module is the piece that makes the audit trail mean something.

**GitHub authenticates; it never authorises.** A successful GitHub login is matched against
`users.github_login`. No row, or `active = false`, means 403 and no session issued: an
authenticated GitHub user is not an authorised INZBC user. Roles come from `user_roles`, which is
data, so changing who holds a role is a data change rather than a deploy.

**What this module deliberately does not do.** It does not perform the OAuth handshake with
GitHub. `establish_session` takes an already-verified GitHub login, so the exchange can be added
without touching the authorisation rules, and so these rules are testable without a network call
or a fake identity provider.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import dict_row

# ADR-0004: absolute 12 hours, idle timeout 60 minutes, whichever comes first.
ABSOLUTE_LIFETIME = timedelta(hours=12)
IDLE_TIMEOUT = timedelta(minutes=60)

# 32 bytes from `secrets` is the standard for a session identifier. The value is the only thing
# standing between an attacker and an authenticated session, so it is not derived from anything
# guessable (user id, timestamp) and never logged.
_TOKEN_BYTES = 32


class AuthenticationError(Exception):
    """No valid session. Maps to 401: the caller may retry after signing in."""


class NotAuthorisedError(Exception):
    """Authenticated, but not permitted. Maps to 403: signing in again will not help.

    Kept distinct from AuthenticationError so the two are never collapsed into one status. A 401
    invites a retry; a 403 says the identity is known and refused, which is what an allowlist
    miss and a missing role both are.
    """


class SelfApprovalError(NotAuthorisedError):
    """The actor is trying to approve, review or check their own work.

    Its own type because this is the separation-of-duties rule in BR8 and ADR-0005, not a
    generic permission failure, and a caller that catches it should be able to say so
    specifically rather than reporting "forbidden".
    """


@dataclass(frozen=True)
class Principal:
    """Who is acting, established from a session rather than supplied by the caller.

    Frozen because a request handler must not be able to widen its own authority partway
    through by assigning to `roles`.
    """

    user_id: str
    name: str
    roles: frozenset[str]
    session_id: str
    csrf_token: str

    def has_role(self, role: str) -> bool:
        return role in self.roles


def _now() -> datetime:
    return datetime.now(UTC)


class SessionRepository:
    """Session storage against Postgres, matching the shape of the other repositories here."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def establish_session(self, github_login: str) -> Principal:
        """Issues a session for an already-authenticated GitHub login.

        Raises NotAuthorisedError when the login has no `users` row or that row is inactive.
        This is the allowlist: authentication having succeeded says nothing about whether this
        person may use the system.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn, conn.transaction():
            user = conn.execute(
                "select id, name, active from users where github_login = %s",
                (github_login,),
            ).fetchone()

            # Same error for "no row" and "inactive", deliberately: distinguishing them tells an
            # unauthenticated caller whether a given GitHub login is registered here.
            if user is None or not user["active"]:
                raise NotAuthorisedError("this GitHub account is not an active INZBC user")

            session_id = secrets.token_urlsafe(_TOKEN_BYTES)
            csrf_token = secrets.token_urlsafe(_TOKEN_BYTES)
            now = _now()
            conn.execute(
                "insert into sessions (id, user_id, csrf_token, created_at, last_seen_at, "
                "expires_at) values (%s, %s, %s, %s, %s, %s)",
                (session_id, user["id"], csrf_token, now, now, now + ABSOLUTE_LIFETIME),
            )
            conn.execute(
                "update users set last_login_at = %s where id = %s", (now, user["id"])
            )
            roles = self._roles_for(conn, user["id"])

        return Principal(
            user_id=str(user["id"]),
            name=user["name"],
            roles=roles,
            session_id=session_id,
            csrf_token=csrf_token,
        )

    def resolve(self, session_id: str) -> Principal:
        """Validates a session id and returns who it belongs to.

        Re-reads `users.active` and `user_roles` on every request rather than trusting what was
        true when the session was issued. That is what makes offboarding immediate: setting
        `active = false` or disabling a role takes effect on the next call, with no session
        cleanup and no deploy.
        """
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn, conn.transaction():
            row = conn.execute(
                "select s.id, s.user_id, s.csrf_token, s.last_seen_at, s.expires_at, "
                "u.name, u.active from sessions s join users u on u.id = s.user_id "
                "where s.id = %s",
                (session_id,),
            ).fetchone()
            if row is None:
                raise AuthenticationError("no such session")

            now = _now()
            if now >= row["expires_at"]:
                conn.execute("delete from sessions where id = %s", (session_id,))
                raise AuthenticationError("session expired")
            if now - row["last_seen_at"] >= IDLE_TIMEOUT:
                conn.execute("delete from sessions where id = %s", (session_id,))
                raise AuthenticationError("session idle too long")

            # An account deactivated after the session was issued. The session is destroyed
            # rather than merely refused, so a re-activation does not silently revive it.
            if not row["active"]:
                conn.execute("delete from sessions where id = %s", (session_id,))
                raise NotAuthorisedError("this account is no longer active")

            conn.execute(
                "update sessions set last_seen_at = %s where id = %s", (now, session_id)
            )
            roles = self._roles_for(conn, row["user_id"])

        return Principal(
            user_id=str(row["user_id"]),
            name=row["name"],
            roles=roles,
            session_id=session_id,
            csrf_token=row["csrf_token"],
        )

    def end_session(self, session_id: str) -> None:
        """Signs out. Deleting the row is the whole mechanism, which is the point of opaque
        server-side sessions: there is no token still valid somewhere else."""
        with psycopg.connect(self._database_url) as conn, conn.transaction():
            conn.execute("delete from sessions where id = %s", (session_id,))

    @staticmethod
    def _roles_for(conn: psycopg.Connection, user_id: str) -> frozenset[str]:
        """Enabled roles only. `user_roles.enabled` exists so a role can be withdrawn without
        deleting the assignment history, and a disabled row must not grant anything."""
        rows = conn.execute(
            "select r.name from user_roles ur join roles r on r.id = ur.role_id "
            "where ur.user_id = %s and ur.enabled",
            (user_id,),
        ).fetchall()
        return frozenset(row["name"] for row in rows)


def require_roles(principal: Principal, *allowed: str) -> None:
    """Refuses unless the principal holds at least one of `allowed`.

    Fail-closed: an empty `allowed` refuses rather than permitting everything, because the
    likeliest way that happens is a caller forgetting to name the roles.
    """
    if not allowed:
        raise NotAuthorisedError("no role permits this action")
    if not any(principal.has_role(role) for role in allowed):
        raise NotAuthorisedError(
            f"requires one of: {', '.join(sorted(allowed))}"
        )


def refuse_self_review(principal: Principal, subject_actor_id: str | None) -> None:
    """Refuses when the principal is acting on their own work.

    BR8 and ADR-0005: a run's analyst may not be its reviewer, and nobody approves their own
    output. A control one person can execute end to end is not a control.

    `subject_actor_id` is whoever produced the thing being acted on. `None` means the record has
    no recorded author, which is not the same as "not the same person": it is permitted here so
    that pre-existing rows do not become unreviewable, and the audit row still names who acted.
    """
    if subject_actor_id is not None and subject_actor_id == principal.user_id:
        raise SelfApprovalError(
            "the person who produced this cannot also review or approve it"
        )
