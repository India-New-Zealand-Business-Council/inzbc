# SIP API contract — v0.1 draft

The interface Roshan (pipeline, writes) and Paras (UI, reads) build against. REST, JSON. Every
write requires authentication, role permission, validation, and an audit-log entry. The
Intelligence Database is the single Action Register — no endpoint creates a competing one.

Auth: bearer token; role from `users.role_id`. Separation of duties enforced server-side
(a run's analyst cannot be its reviewer; nobody approves their own output).

## Pipeline (Roshan) — data in
```
POST   /api/runs                     create a run (fixes the 24h coverage window)
GET    /api/runs        /api/runs/:id
POST   /api/runs/:id/start | /pause | /resume | /complete
GET    /api/runs/:id/source-checks
POST   /api/runs/:id/source-checks   record a per-source outcome (mandatory sources must have one)
GET    /api/candidates?run=:id
POST   /api/candidates               capture a candidate (all scoring/verification fields)
PATCH  /api/candidates/:id
POST   /api/candidates/:id/verify | /score | /route | /merge
```

## Control (Paras) — data out + human gates
```
POST   /api/reports/daily            build the SIP-186 brief from selected candidates
GET    /api/reports/:id
POST   /api/reports/:id/qa           record SIP-188 QA result (blocks release on Critical)
POST   /api/reports/:id/submit
POST   /api/reports/:id/approve | /request-changes
POST   /api/reports/:id/decision     CEO decision + distribution authority (no auto-send)
GET    /api/registers/:name          action | watch | opportunities | threats | exceptions
POST   /api/registers/:name
GET    /api/dashboard                control state, open actions, QA/distribution status
```

## Cross-cutting
```
GET    /api/audit                    append-only audit log (read)
GET    /api/config                   server-side control flags (read)
```

## Rules every write endpoint enforces
- Fail-closed: a Critical condition (missing run authority, unapproved version, missing mandatory
  source outcome, unverified Critical claim, tracker/DB contradiction, missing approval,
  unauthorised distribution) returns an error, never a warning.
- Server-side flags stay false unless a controlled approval record exists:
  `production_enabled`, automated/member/external/website/social distribution.
- No secrets in requests, responses, or logs.

Full OpenAPI spec lands here as the app is built. This draft freezes the endpoint shapes so
pipeline and UI can start in parallel.
