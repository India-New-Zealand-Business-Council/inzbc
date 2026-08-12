# Backup and run-monitoring design

Two operational designs that share a premise: **a system nobody is watching fails silently, and a
backup nobody has restored is a belief rather than a control.**

Written for the organisation that holds this after the placement ends — one person, free-tier
hosting, no operations team. A design assuming PagerDuty and a rota would be ignored, so this one
assumes email and a habit.

---

# Part 1: Run monitoring

## What actually needs watching

A SIP run passes through eleven states, and three of them are **human gates** — the run stops and
waits for a person. So there are two completely different failure modes, and conflating them is
how monitoring ends up useless:

**The run broke.** A collector failed, the model refused, the database was unreachable. This needs
an alert.

**The run is waiting for someone.** `Awaiting CEO Decision` is not a failure — it is the control
working. But a run that has been waiting three days *is* a problem, and it looks identical to a
healthy one at any single moment.

Most monitoring only catches the first. The second is the one that will actually bite here,
because a one-person organisation is exactly where a run sits forgotten in a gate.

## Signals

| Signal | Source | Means |
|---|---|---|
| Run started | `run.create` in `audit_log` | A run exists |
| Run reached each gate | `run.transition` | Normal progress |
| Run finished | transition to `Closed` | Success |
| Run failed QA | transition to `QA Failed` | The reviewer's stop; expected, not an error |
| **Run stalled in a gate** | no `run.transition` for N hours | The one that needs designing (below) |
| **No run started today** | no `run.create` since 00:00 | The silent failure — nothing broke because nothing ran |
| Model call refused | `RedactionNotConfiguredError` | Fail-closed working, or misconfiguration |
| Collector source failed | collector's own record | Degraded input, not a stopped run |

**The two rows in bold are the ones no ordinary monitoring tool would give you**, because both are
absences. A tool watching for errors sees a perfectly quiet system.

**Everything here reads from `audit_log`.** That is deliberate: the audit trail is already
append-only, already transactional with the mutation it records, and already required by BR1. A
separate metrics store would be a second source of truth about what happened, and the two would
disagree eventually.

## Thresholds

Starting points, to be tuned once there is real operating history rather than guessed precisely
now:

| Condition | Threshold | Action |
|---|---|---|
| No run started | by 10:00 on a working day | Email the SIP Owner |
| Run in a non-gate state with no transition | 60 minutes | Email — a machine state should not take an hour |
| Run in a human gate with no transition | 24 hours | Email the person the gate is waiting on |
| Run in a human gate | 72 hours | Escalate to the Executive Sponsor |
| `/health` failing | 5 minutes | Email |

**Human gates get a longer threshold than machine states**, and that asymmetry is the whole point
of the table. An hour in `Scanning` means something hung. An hour in `Awaiting CEO Decision` means
someone is in a meeting.

## Alerting

**Email, and nothing more, deliberately.** It is free, it reaches one person reliably, and the
alternative — a dashboard — requires someone to go and look, which is precisely what does not
happen in a one-person organisation.

**Every alert names the run and what to do.** An alert that says "run failed" sends the reader to
the logs to find out what they already needed to know. An alert reading *"Run 47 has been in
Awaiting CEO Decision since Tuesday 09:12. Decide at /runs/47"* is actionable without opening
anything.

**Alerts must be rare enough to still be read.** If the daily-run alert fires most days, it stops
being an alert and becomes a newsletter. The threshold to tune first is whichever one fires most.

## `/health` is weaker than it looks

`GET /health` returns `{"status": "ok"}` unconditionally. It proves the process is running and
serving HTTP. It does **not** prove the database is reachable, that migrations are applied, or that
a run could actually be created.

That is a defensible liveness probe and a poor readiness check, and the distinction matters here
because the host's health check is currently the only automated thing watching the system at all.
A readiness variant that touches the database — one cheap `select 1` — would turn "the container is
up" into "the system works", which is a different claim.

Deliberately not adding it in this document: it is a code change with a real trade-off (a
readiness check that fails on a slow database can cause a restart loop that makes an outage worse),
and it should be decided rather than slipped in.

---

# Part 2: Backup

## What needs backing up, honestly

| What | Backed up today | Actually recoverable? |
|---|---|---|
| Postgres — runs, candidates, decisions, audit | Whatever the host provides | **Unproven.** Never restored |
| The Wix site | Wix Site History | Partly. Does not reliably cover CMS or app data |
| The repositories | GitHub, plus every clone | Yes. Genuinely fine |
| Secrets | Nowhere by design | Rotate, do not restore |
| The built container image | Rebuildable from source | Yes, and rebuilding is better than restoring |

**Only one row is a real problem**, and it is the row holding every approval, every decision and
the append-only audit trail — the records the whole system exists to produce.

## Cadence and retention

| Data | Frequency | Keep |
|---|---|---|
| Postgres full | Daily | 30 days |
| Postgres point-in-time | Continuous, if the host offers it on the free tier | 7 days |
| Wix Site History | Before each publish, recorded in `wix-changes-log.md` | Until the new version is stable for a month |
| Repositories | On every push | Indefinite |

**Thirty days is a privacy decision as much as an operational one.** A backup kept for two years
holds personal data two years after its retention period expired everywhere else, which quietly
defeats the deletion rules. Long enough to notice a problem, short enough not to become a shadow
archive.

## Where backups live

**Not in the same account as the thing being backed up**, which is the failure this row exists to
prevent: an account lockout takes the backup with the system. BR11 applies here too — the backup
location must be organisation-owned, not personal.

`[[to confirm]]` — the host's backup offering on the free tier has not been checked, and it may
not include point-in-time recovery. If it does not, a scheduled `pg_dump` to organisation-owned
storage is the fallback, and it is a small script rather than a project.

## The restore path

**The procedure and its checker now exist:** [`restore-procedure.md`](./restore-procedure.md) and
`scripts/verify_restore.py`, which runs on every CI build against a schema applied to an empty
database. What cannot be proven yet is a restore of a *production* backup, because there is no
production database (#99).

The steps, in short:

1. Provision an empty database.
2. Apply the backup.
3. Confirm the schema matches `database/schema.sql`.
4. Start the API against it and confirm `GET /api/runs` returns.
5. Spot-check that the append-only triggers survived the restore — a restored `audit_log` without
   its trigger is mutable, and nothing would tell you.
6. Record the date, the elapsed time, and anything that surprised you.

**Step 5 is the one that would be skipped**, and it is the one that would matter. Triggers and
grants are schema objects; a restore that recreates tables and rows but not `audit_log_append_only`
leaves the audit trail editable while looking completely normal. `scripts/verify_restore.py` does
step 5 for you, and goes further: it tries an update on an audit row and requires the refusal,
because a trigger that exists and does not fire passes a catalogue check.

**Step 6's elapsed time is the actual deliverable.** "We have backups" is not a recovery position.
"We can be back in forty minutes and here is when we last proved it" is.

## What a restore cannot recover

Stated plainly, because BR12 requires a tested restore and a plan that overstates itself fails the
first time it is used.

- **Anything since the last backup.** With daily backups that is up to a day of runs and decisions.
- **Wix CMS and app data**, which Site History does not reliably hold.
- **Secrets.** They are not in the backup by design. Rotate them and update the deployment.
- **The relationship between the database and external services.** A restored run referencing an
  EmailOctopus send that already happened does not un-send it.

## Review

Restore tested at least **quarterly**, alongside the access review in
[`incident-response.md`](./incident-response.md) — same sitting, same record. An untested backup
degrades silently: the host changes a default, a table is added, a grant is missed, and none of it
surfaces until the day it is needed.
