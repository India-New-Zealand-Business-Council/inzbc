# services/api — shared API, auth, audit

Owner: Bhanu. Implements `schemas/api-contract.md` over `database/schema.sql`. Enforces auth,
RBAC, validation, audit logging, and the fail-closed control flags server-side.

## Running it

```bash
pip install -e ".[dev]"
uvicorn services.api.main:app --reload
```

`GET /openapi.json` serves the schema the TypeScript client is generated from — never hand-write
that client (ADR-0001).

## What exists today

| Surface | Status |
|---|---|
| `GET /api/fta/query` | Live. Reads the sourced FTA corpus; no database, no auth |
| `GET /health` | Live. Liveness probe for the host health check (ADR-0004) |
| `model_gateway.py` | Live. The single server-side model-call path |
| `persistence.py` | Live (#117). Postgres `runs` adapter with optimistic concurrency |
| `audit.py` | Live (#118). Transactional audit writes into an append-only `audit_log` |
| Run, candidate, report and decision endpoints | Not built — need the database and the orchestrator's persistence |

Auth and RBAC are not implemented yet, and the run/candidate endpoints do not exist, so nothing here
is reachable by staff and `production_enabled` stays `false`; the adversarial security review in
`docs/sip/README.md` gates any staff use.

## Audit trail (#118)

Every state-changing write records `old_value`/`new_value`/`reason`/`approval_ref` in `audit_log`
**inside the mutation's own transaction** (`audit.record_audit`, called on the caller's connection),
so a change and its audit record commit together or not at all. `create_run` and
`apply_transition` are both wired this way.

The database does not itself require an audit row when `runs` changes, so this holds because
every writer here does it, not because the schema compels it. A new write path, or direct SQL,
can still omit one. Immutability, by contrast, is enforced by the database rather than by
convention:

- an `audit_log_append_only` trigger refuses `UPDATE`/`DELETE` from any role, and an
  `audit_log_no_wipe` statement trigger refuses a whole-table clear, which a row trigger
  never sees (`database/schema.sql`);
- the application login role is granted `INSERT`/`SELECT` only. That grant lives in
  `database/audit_role.sql`, applied against a deployed database after `schema.sql`:

  ```bash
  psql "$DATABASE_URL" -v app_role=inzbc_app -f database/audit_role.sql
  ```

  It is kept out of `schema.sql` because CI applies the schema with no application role existing.

## The FTA response envelope

`GET /api/fta/query` returns a status-tagged envelope, not a list that might be empty:

```json
{ "status": "matched",  "query": "dairy", "answers": [ ... ], "action_required": null }
{ "status": "no_match", "query": "zzzz",  "answers": [],      "action_required": { ... } }
```

**Branch on `status`, never on `answers.length`.** A no-match is a designed outcome carrying an
escalation path, not an empty result set — a client that checks only the array silently drops the
guidance that `docs/modules/fta-centre.md` requires. `action_required` deliberately carries no
`topic`, `treatment` or `citation`, so escalation cannot be rendered as a sourced finding. A model
validator rejects any envelope where the tag and the payload disagree.
