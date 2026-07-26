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
| Run, candidate, report and decision endpoints | Not built — need the database and the orchestrator's persistence |

Auth, RBAC and the audit log are not implemented yet. Nothing here is reachable by staff, and
`production_enabled` stays `false`; the adversarial security review in `docs/sip/README.md` gates
any staff use.

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
