# Restoring the database, and proving it worked

BR12 and objective O6 name a **tested** restore. The design is in
[`backup-and-monitoring.md`](backup-and-monitoring.md); this is the procedure, written so the
operator can run it without the people who built the system.

**The reason this document exists.** An untested backup is a belief. The belief that fails is
always the same one: *the rows came back, so the restore worked.* Rows are the easy part.

## What has actually been proven

Being precise about this, because a procedure that overstates its own evidence is worse than none.

| Claim | Status |
|---|---|
| The verification script works against a schema applied to an empty database | **Proven.** It runs on every CI build |
| The schema carries every append-only guard it claims | **Proven.** Same run |
| A backup of the platform database restores | **Not proven.** No production database exists yet (#99) |
| How long a restore takes | **Unknown.** Nothing to time |

So the *check* is real and running. The *restore* cannot be tested until there is a production
database to back up. Wiring the check into CI now means that on the day there is one, the hard part
is already built and exercised, rather than being written under pressure.

## The procedure

### 1. Restore into an empty instance

Never over the top of a working database. A restore that half-succeeds onto live data leaves you
with neither.

```
createdb inzbc_restore_test
pg_restore --dbname=inzbc_restore_test --no-owner --no-privileges <backup-file>
```

**Time this step.** It is the number the recovery plan rests on, and it is the one nobody has.
"We have backups" is not a recovery position; "we can be back in forty minutes, proven on 12
August" is.

### 2. Run the checker

```
python scripts/verify_restore.py "postgresql://.../inzbc_restore_test"
```

It exits non-zero and names the problem if anything is wrong. Four things get checked, in
increasing order of what they catch:

**Tables exist.** The obvious one. Every core and evidence table present.

**Evidence row counts, reported not asserted.** Zero is legitimate for an empty database, so it is
not a failure. It is printed because a count that is zero when you expected thousands is the
fastest way to notice you restored the wrong backup.

**The append-only triggers came back.** *This is the step a manual check skips, and it is the one
that matters.* Triggers are schema objects, not data. A restore that recreates every table and
every row but drops `audit_log_append_only` leaves the audit trail silently editable, and nothing
about the database looks wrong. Both guards are checked per table: the row trigger, and the
whole-table one, because a row trigger never fires for a single-statement wipe.

**The immutability actually holds.** The catalogue check proves a trigger *exists*. This proves it
*fires*, by attempting an update on an audit row and requiring the refusal. A trigger restored
without its function, or left disabled, is present in `pg_trigger` and does nothing, so the
catalogue check passes and the guarantee is gone. The attempt runs inside a transaction that is
always rolled back.

### 3. Start the API against it

```
DATABASE_URL="postgresql://.../inzbc_restore_test" uvicorn services.api.main:app
```

Then `GET /api/runs`. A schema that restores and an application that runs are different claims.

### 4. Record it

In [`backup-and-monitoring.md`](backup-and-monitoring.md), or the operator's own log:

- The date.
- How long the restore took.
- Anything that surprised you.

**A restore nobody timed cannot be planned around**, and a review nobody can prove happened has
the same evidential value as one that did not.

### 5. Drop the test database

It is a full copy of everything, including staff personal data and the complete record of who did
what. Leaving it lying around is a second copy of the most sensitive data in the system, in a
place with no access controls and nobody's name on it.

## When to run this

- **Quarterly**, in the same sitting as the access review in
  [`incident-response.md`](incident-response.md).
- **After any schema change**, because that is when a trigger or grant goes missing.
- **Before handover**, with the timing recorded. This is the evidence BR12 asks for.

## What a restore cannot recover

Repeated from the backup design because this is where it gets read:

- Anything since the last backup. With daily backups that is up to a day of runs and decisions.
- Grants. `database/audit_role.sql` provisions the restricted application role outside `schema.sql`,
  so a restored database may have the triggers and not the role. The triggers are the backstop, not
  the primary control, and the primary one has to be re-applied.
- Secrets. Not in the backup by design. Rotate and update the deployment.
- The relationship to external services. A restored run referencing a send that already happened
  does not un-send it.

The second item is the quiet one. The checker verifies the triggers, and the schema itself says the
grant is "the real append-only boundary" with the trigger catching a mistake by a role that could
otherwise edit. A restore that reinstates the triggers and not the grant leaves the weaker half of
a two-part control, and looks completely healthy.
