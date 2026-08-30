# Migrations

`database/schema.sql` is the baseline. Every schema change after 20 August 2026 is a numbered file
in this directory, applied once, in filename order, each inside its own transaction.

Closes #44, which was blocked on the hosting decision until ADR-0004 graduated the platform.

## Commands

```
DATABASE_URL=... python scripts/migrate.py status     # what is applied, what is pending
DATABASE_URL=... python scripts/migrate.py up         # apply everything pending
DATABASE_URL=... python scripts/migrate.py baseline   # record an already-built database
```

## Setting up

**A new database:**

```
psql "$DATABASE_URL" -f database/schema.sql
python scripts/migrate.py baseline
python scripts/migrate.py up
```

**A database that already exists** — anything built before this runner did:

```
python scripts/migrate.py baseline    # records the baseline, runs nothing
python scripts/migrate.py up
```

`baseline` never executes `schema.sql`. It records it as applied, because re-running it against a
built database would error on the first object that already exists.

## Writing one

Name it `NNNN_short_description.sql`, taking the next number. Put the reason in a comment at the
top — the file is the only place a future reader will look for why the change happened.

Write it so it is safe to run against a database that already has the change (`if not exists`,
`add column if not exists`). A database built fresh from `schema.sql` already carries everything
in `schema.sql`, so a migration that also appears there must be a no-op on it.

**Update `schema.sql` in the same pull request.** The baseline stays the current full picture; the
migration is how existing databases catch up. They are not alternatives.

## Rules the runner enforces

It refuses rather than guesses, in four cases:

| Situation | Why refusing is right |
|---|---|
| `up` with no baseline recorded | Applying migration 0001 to a database with no tables produces a confusing failure instead of a clear one |
| `baseline` on an empty database | There is nothing to baseline. Recording one would skip the entire schema forever |
| An applied migration's contents changed | Two databases would disagree and nothing would say so. Write a new migration |
| `schema.sql` changed after being baselined | Same reason. The baseline is immutable once recorded — see recovery below |

A session-level advisory lock serialises concurrent runners.

## Recovering from the baseline-drift refusal

`schema.sql` is updated in the same pull request as every migration, so its checksum goes stale on
every change — which, as first shipped, blocked `up` permanently on every already-baselined
database with no way out. That was a trap, not a control. Found by adversarial review of #303.

```
python scripts/migrate.py rebaseline
```

Re-records the checksum and runs no SQL.

It is a separate, explicitly-named command rather than something `up` does silently, because the
one case where the refusal is *correct* — the database genuinely does not have the change — is
exactly the case a silent fix would hide. **Confirm the change reached the database before running
it.** Rebaselining a database that is actually behind records a lie.

## Forward-only, deliberately

There are no `down` migrations. A rollback script is written once and run never, so it is never
tested, and an untested rollback is worse than none because it invites trust it has not earned. To
undo a migration, write the next one.

## Why not Alembic

It would bring SQLAlchemy, which this repository does not use — everything talks to Postgres
through raw psycopg and raw SQL. A tracking table and a loop cover the same ground in one file
with no new dependency. If migrations ever need branching or autogeneration, revisit it then.

## Concurrent index creation

`CREATE INDEX` holds a write lock for its duration. `CREATE INDEX CONCURRENTLY` avoids that but
cannot run inside a transaction, and this runner wraps every migration in one deliberately.

No production database exists yet (#99), so there is nothing to block. Before the first deploy,
decide whether index migrations need an escape hatch from the per-migration transaction.
