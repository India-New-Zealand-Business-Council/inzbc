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

import hashlib
import secrets
import uuid
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


def storage_id(token: str) -> str:
    """What gets stored for a session token, given the value the browser holds.

    Public because tests and any future session-maintenance job need to address a row by the
    same transformation the repository uses. A private helper would push callers into
    re-implementing the hash, which is how the stored form and the lookup form drift apart.

    The cookie value itself is never written to the database. A read-only database snapshot, a
    backup, or SQL access would otherwise hand over live sessions: copy `sessions.id`, send it as
    the cookie, call `GET /api/session` for the CSRF token, and act as that user until expiry.
    Storing only the digest makes a leaked table useless for replay.

    Plain SHA-256 with no salt is correct here, unlike for passwords. The input is 32 random
    bytes, so there is no dictionary to attack and nothing a per-row salt would defend against;
    what matters is that the stored value cannot be replayed.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _canonical_actor(value: str | uuid.UUID | None) -> str | None:
    """Normalises an actor id so comparisons cannot be defeated by formatting.

    `'A1B2...'`, `'a1b2...'`, the unhyphenated form and a `uuid.UUID` object are all the same
    principal. Comparing the raw strings would let an uppercase or unhyphenated id slip past the
    self-review check, which is a silent authorisation bypass rather than an error.

    Anything that is not a well-formed UUID returns `None`, so a malformed value can never
    compare equal to a real one.
    """
    if value is None:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return None


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
        # GitHub logins are case-insensitive, so `Alice` and `alice` are one account. Matching on
        # the raw string would let provisioning create two rows for the same person, with
        # different roles, and which one you got would depend on how you typed it.
        login = github_login.strip().lower()
        if not login:
            raise NotAuthorisedError("this GitHub account is not an active INZBC user")

        with psycopg.connect(self._database_url, row_factory=dict_row) as conn, conn.transaction():
            user = conn.execute(
                "select id, name, active from users where lower(github_login) = %s",
                (login,),
            ).fetchone()

            # Same error for "no row" and "inactive", deliberately: distinguishing them tells an
            # unauthenticated caller whether a given GitHub login is registered here.
            if user is None or not user["active"]:
                raise NotAuthorisedError("this GitHub account is not an active INZBC user")

            session_id = secrets.token_urlsafe(_TOKEN_BYTES)
            csrf_token = secrets.token_urlsafe(_TOKEN_BYTES)
            now = _now()
            # Only the digest is stored; `session_id` goes to the browser and nowhere else.
            conn.execute(
                "insert into sessions (id, user_id, csrf_token, created_at, last_seen_at, "
                "expires_at) values (%s, %s, %s, %s, %s, %s)",
                (storage_id(session_id), user["id"], csrf_token, now, now, now + ABSOLUTE_LIFETIME),
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
        stored_id = storage_id(session_id)
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            row = conn.execute(
                "select s.id, s.user_id, s.csrf_token, s.last_seen_at, s.expires_at, "
                "u.name, u.active from sessions s join users u on u.id = s.user_id "
                "where s.id = %s",
                (stored_id,),
            ).fetchone()
            if row is None:
                raise AuthenticationError("no such session")

            now = _now()
            failure: Exception | None = None
            if now >= row["expires_at"]:
                failure = AuthenticationError("session expired")
            elif now - row["last_seen_at"] >= IDLE_TIMEOUT:
                failure = AuthenticationError("session idle too long")
            elif not row["active"]:
                # An account deactivated after the session was issued.
                failure = NotAuthorisedError("this account is no longer active")

            if failure is not None:
                # The delete has to commit before the raise, in its own transaction. An earlier
                # version deleted and raised inside one `conn.transaction()` block, so the
                # exception rolled the delete straight back: the call was refused, but the row
                # survived every time. The session was never actually destroyed, which is the
                # property the refusal is supposed to carry - a re-activated account would have
                # silently revived its old session.
                with conn.transaction():
                    conn.execute("delete from sessions where id = %s", (stored_id,))
                raise failure

            with conn.transaction():
                conn.execute(
                    "update sessions set last_seen_at = %s where id = %s", (now, stored_id)
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
            conn.execute("delete from sessions where id = %s", (storage_id(session_id),))

    def purge_expired(self) -> int:
        """Deletes sessions past their absolute expiry or idle window. Returns how many.

        Expired rows are otherwise only removed when that same token is presented again, so an
        abandoned session lives forever. Nothing calls this on a schedule yet; it exists so the
        cleanup is a function to invoke rather than a migration to write later.
        """
        with psycopg.connect(self._database_url) as conn, conn.transaction():
            result = conn.execute(
                "delete from sessions where expires_at <= %s or last_seen_at <= %s",
                (_now(), _now() - IDLE_TIMEOUT),
            )
            return result.rowcount

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


def refuse_self_review(principal: Principal, subject_actor_id: str | uuid.UUID | None) -> None:
    """Refuses when the principal is acting on their own work, or when authorship is unknown.

    BR8 and ADR-0005: a run's analyst may not be its reviewer, and nobody approves their own
    output. A control one person can execute end to end is not a control.

    **Unknown authorship refuses.** An earlier version permitted `None`, reasoning that records
    with no recorded author should not become unreviewable. That was fail-open: the check cannot
    tell "nobody wrote this" from "we failed to read who wrote it", and anyone able to arrange a
    null author would have been able to approve their own work. A record whose author cannot be
    established needs its authorship backfilled, or a recorded `sod_exceptions` row, not a silent
    pass.

    Both ids are canonicalised before comparing, so an uppercase or unhyphenated UUID cannot slip
    past. A malformed id canonicalises to `None` and is therefore refused, not permitted.
    """
    subject = _canonical_actor(subject_actor_id)
    if subject is None:
        raise SelfApprovalError(
            "cannot establish who produced this, so separation of duties cannot be checked"
        )
    if subject == _canonical_actor(principal.user_id):
        raise SelfApprovalError(
            "the person who produced this cannot also review or approve it"
        )
