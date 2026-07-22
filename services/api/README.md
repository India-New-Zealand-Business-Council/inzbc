# services/api — shared API, auth, audit

Owner: Bhanu. Implements `schemas/api-contract.md` over `database/schema.sql`. Enforces auth,
RBAC, validation, audit logging, and the fail-closed control flags server-side.
