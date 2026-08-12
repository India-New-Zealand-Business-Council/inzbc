# Development, test and production environments

A Phase 1 deliverable and a mandatory security control. The reason it is urgent is not that the
current setup is dangerous — it is that **production does not exist yet** (#99), and separating
environments before there is production data is nearly free. Doing it afterwards means a migration.

## What exists today

| Environment | Where | Data | Lifetime |
|---|---|---|---|
| Development | A developer's machine | Whatever that developer created | Permanent, uncontrolled |
| Test | GitHub Actions, `postgres:16.2` service container | Synthetic, built by fixtures | One CI run, then destroyed |
| Production | **Does not exist** | — | — |

Test is in better shape than it looks: an ephemeral database per run, `database/schema.sql` applied
fresh, and fixtures that construct their own users and candidates rather than copying real ones. It
is genuinely isolated, and it stays that way by being thrown away.

**The gap is development.** It is a long-lived database on a personal machine with no defined
contents, and it is the one that will quietly acquire a copy of production data the first time
someone debugs a real problem.

## The rules

Four, and they are worth more than any amount of tooling:

**1. Production data never leaves production.** Not into a development database to reproduce a
bug, not into a test fixture, not into a screenshot in a document, not into a client demonstration.
Debugging against a copy of production is the single most common way personal data ends up
somewhere with no access controls.

**2. Each environment holds its own credentials.** A development environment holding the production
OpenAI key is a production credential protected by a laptop. Each environment gets its own, and
`secrets-register.md` records which is which.

**3. Test data is synthetic, and that is a rule rather than a habit.** The suite already works this
way. Writing it down is what keeps it true when someone is in a hurry.

**4. Only CI deploys to production.** Not a laptop. A deployment from a developer's machine has no
record of what was deployed, cannot be reproduced, and skips every check.

## What separation actually requires

Modest, because the application was built for it:

| Piece | Status | Work |
|---|---|---|
| Config from environment, not code | **Done** — `DATABASE_URL`, `REDACTION_POLICY_PATH`, `PORT` are all read from the environment | None |
| One image, many environments | **Done** — the Dockerfile takes no environment-specific build argument | None |
| Schema applied identically everywhere | **Partly** — CI applies `schema.sql` from scratch; there is no migration path for a database that already has data | #44 |
| Separate databases | Development and CI yes; production not created | With #99 |
| Separate credentials | Not defined | This document, then the register |
| Deployment from CI only | Not built | With #99 |

**The one genuine gap is #44.** Applying `schema.sql` to an empty database is not the same as
evolving a database that already holds rows, and once production exists, every schema change needs
to be a migration rather than a re-apply. That is the piece that has to land before production
carries data worth keeping — which, given the append-only audit trail, is from the first run.

## Configuration per environment

| Variable | Development | Test (CI) | Production |
|---|---|---|---|
| `DATABASE_URL` | Local Postgres | Ephemeral service container | Managed Postgres, its own credential |
| `REDACTION_POLICY_PATH` | Unset, or a test policy | Set by the test that needs it | The approved policy — until then, every model call refuses |
| `OPENAI_API_KEY` | A separate development key, or unset | Unset; no test calls a provider | Production key, environment only |
| `PORT` | 8000 | — | Injected by the host |

**`REDACTION_POLICY_PATH` unset means refusal, not permission.** So an environment that has not
been configured fails closed rather than sending unredacted text to a model. That is the correct
default and it should stay the default in every environment, including production, until the policy
file is deliberately placed.

## Promotion

```
developer machine  ──►  pull request  ──►  CI (ephemeral db, full suite)  ──►  main  ──►  production
```

**Nothing reaches production without passing through `main`, and nothing reaches `main` without
CI.** Nine jobs are the gate: `validate` (JSON), `linked-issue`, `docker` (build and endpoint
check), `python` (ruff and pytest with coverage against a real Postgres), `frontend`, `sast`
(semgrep), `security` (gitleaks), `workflows` (actionlint) and `links`.

All nine block the merge. `sast` was report-only until its baseline was confirmed clean (#70); it
now fails on any semgrep finding.

**Deployment is from `main` only, by CI**, so what is running is always a commit someone can point
at.

## What this does not solve

**There is still no staging environment** — somewhere production-shaped, with production-shaped
data volumes, that is not production. For this engagement that is the right call: a third
environment on free-tier hosting costs more attention than it returns, and the highest-risk change
(the website cutover) has its own reversible plan in
[`migration-and-rollback.md`](./migration-and-rollback.md) rather than relying on a rehearsal
environment.

It becomes the wrong call the moment there is a schema migration to rehearse against real data
volumes. That is the trigger to revisit, and #44 is what will bring it.

## Before production is created

1. Its own database, its own credentials, registered in [`secrets-register.md`](./secrets-register.md).
2. Migrations rather than schema re-application (#44).
3. Deployment from CI on `main`, not from a machine.
4. Backups configured before the first run, not after ([`backup-and-monitoring.md`](./backup-and-monitoring.md)).
5. The four rules above written into the operator guide, so they survive this team.
