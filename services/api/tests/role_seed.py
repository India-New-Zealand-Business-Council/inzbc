"""Seeding roles for the database-backed suites, keyed on name rather than id.

Every suite here shares one database, and `roles.name` is unique while `roles.id` is not
coordinated between them. Three suites claim id 1 as `Analyst`; `test_decisions.py` claims id 1 as
`SIP Owner`. With `on conflict do nothing`, whichever suite runs first wins the name at that id and
the others silently get a role called something else.

That was harmless while nothing read `roles.name`: the foreign key only needs the id to exist. Role
enforcement reads the name to decide authority, so the same seed now produces a principal whose
permissions depend on test execution order.

Seeding by name fixes it: ask for the role you want, get its real id back whatever id it happens to
live at.
"""

from __future__ import annotations

import psycopg


def role_id(conn: psycopg.Connection, name: str) -> int:
    """Returns the id of the role called `name`, creating it if absent.

    `on conflict (name) do update` rather than `do nothing`, because `do nothing` suppresses the
    `returning` clause when the row already exists and hands back `None`. The update is a no-op
    write whose only job is to make the existing row's id available.
    """
    row = conn.execute(
        "insert into roles (id, name) values "
        "((select coalesce(max(id), 0) + 1 from roles), %s) "
        "on conflict (name) do update set name = excluded.name returning id",
        (name,),
    ).fetchone()
    return row[0] if not isinstance(row, dict) else row["id"]


def grant(conn: psycopg.Connection, user_id: str, *names: str) -> list[int]:
    """Gives `user_id` each named role, enabling any assignment that already exists."""
    ids = []
    for name in names:
        rid = role_id(conn, name)
        conn.execute(
            "insert into user_roles (user_id, role_id) values (%s, %s) "
            "on conflict (user_id, role_id) do update set enabled = true",
            (user_id, rid),
        )
        ids.append(rid)
    return ids
