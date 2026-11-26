# INZBC Platform — Viva Walkthrough (Simple + Technical)

## 1. How the Whole App Works (In 1 Sentence Each)
- **Simple:** Staff open one web dashboard; every button calls our backend API, which lets automation do the boring news-gathering work but **physically locks** every approval door until a real human signs off — and stamps every signature cryptographically into PostgreSQL so nobody can fake or edit history.
- **Technical:** A React 18 / TypeScript unified shell (`AppShell.tsx`) communicates over HTTP/SSE with a globally hardened FastAPI gateway (`services/api/main.py`, 82 OpenAPI operations), backed by a fail-closed Python state machine (`orchestrator.py`), server-side HMAC-SHA256 + SHA-256 hash-chained audit seals (`audit_seal.py`, ADR-0010), and PostgreSQL 16.2 (30 tables, 16 append-only triggers, `pgvector`).

---

## 2. File-by-File: Simple vs. Technical

| File | Simple Language (Plain English) | Technical Language (Engineering Terms) |
| --- | --- | --- |
| **1. `01_ENV_CONFIG.env`** | The secret locker. Passwords and API keys stay out of code; AI features stay **off** unless explicitly switched on. | Gitignored `.env` / GitHub Actions secrets; fail-closed `COMMS_EXTERNAL_MODEL_ENABLED`, server-only `SIP_DECISION_SIGNING_KEY` (≥32B), `DATABASE_URL`, gated by `gitleaks` CI. |
| **2. `02_BACKEND_API_main.py`** | The single front door for the whole platform. Every request passes through one security checkpoint before reaching any feature. | FastAPI ASGI app mounting 20 domain routers (82 OpenAPI ops) behind global `install_hardening(app)` middleware (rate limits, CORS, headers, uniform errors), RBAC tiers (`STAFF_READ` / internal), and strict Pydantic v2 (`extra="forbid"`) contracts. |
| **3. `03_FAIL_CLOSED_ORCHESTRATOR.py`** | The rulebook enforced by code, not trust. The AI can suggest the next step, but 11 locked doors require a real human decision — and a stopped run can never be restarted. | Immutable `MappingProxyType` transition graph (`_LEGAL`), 11 `_HUMAN_GATED` transitions requiring frozen `HumanDecision` objects, fail-closed exceptions (`IllegalTransition`, `HumanGateRequired`, `RunTerminated`). Blocks **48/48** gate-safety attacks. |
| **4. `04_CRYPTO_AUDIT_SEAL.py`** | Wax seal + tamper-proof ledger. When a human clicks approve, the server signs it with a secret key the AI can never see, and chains every log entry together so editing even one letter breaks the chain. | ADR-0010 Option B (Schneier & Kelsey, 1999): domain-separated HMAC-SHA256 decision signatures verified with constant-time `hmac.compare_digest` (**200/200** forged approvals caught) + canonical JSON SHA-256 hash chain MACed at head (**1,000/1,000** metadata edits & **759/759** Postgres rewrites caught). |
| **5. `05_FRONTEND_AppShell.tsx`** | One clean website uniting all 4 tools (Daily Brief, FTA Tariff Finder, Comms Drafter, Member Portal). Buttons stay disabled until the database proves earlier human approvals happened. | React 18 + TS + Tailwind (WCAG 2.2 AA) shell calling `runsClient.ts` (`listRuns`), hydrating `briefForRun` from live PostgreSQL state without placeholder fabrication, enforcing UI-level `TERMINAL` locks and `BriefSection.pending` QA friction (PR `#553`). |

---

## 3. Numbers to Remember for Viva Questions
- **Scale:** 82 OpenAPI ops · 30 PostgreSQL tables · 16 append-only triggers · 11 migrations · 9/9 CI jobs green.
- **Tests:** **1,794** Python tests on real Postgres (`94.64%` coverage) + **481/481** frontend UI tests (`main @ 1f7e330`, PR `#588` merged).
- **Safety Proof:** **48/48** gate attacks blocked · **0/35** breaches in live hostile runs · **200/200** forged approvals caught · **759/759** DB rewrites caught · **8/8** Quality Judge golden-set agreement (`κ = 1.0`).
- **Live Bugs Caught & Fixed:** PR `#583` (Platform Assistant read-tool shorthand/guide) & PR `#588` (7 `record_audit()` kwargs mismatches in `sponsors_persistence.py` + AST contract test).
