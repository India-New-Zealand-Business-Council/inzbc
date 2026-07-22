# ADR-0001: Backend language and contract strategy

- Status: Accepted
- Date: 2026-07-22
- Deciders: Bhanu (tech lead), with Roshan and Paras

## Context
AIOS has three engineers and a near-zero running-cost constraint. The SIP collection agent already
exists in Python (`daily-india-nz-news-agent`: openai/perplexity/feedparser). Paras's frontend is
Wix Velo, which is JavaScript/TypeScript and not a choice. The platform is a controlled
intelligence system: it must be auditable, fail-closed, and enforce human-approval gates. The
team ships in weeks, not months, and none of the three are specialists in exotic type systems.

The real risk is not raw language power. It is (a) two backend "language worlds" drifting apart so
the three cannot review each other's code, and (b) the backend and the Velo frontend
re-implementing the same contract and diverging.

## Decision
1. **Backend: Python (FastAPI + Pydantic)** for both the pipeline (Roshan) and the shared API,
   auth, audit, and run state machine (Bhanu). One backend language the whole team reads.
2. **Contract-first.** The API is defined by Pydantic models and published as OpenAPI. The
   **TypeScript types for Velo are generated from that OpenAPI**, so the frontend and backend share
   one source of truth and cannot drift.
3. **Frontend: TypeScript (Velo)**, consuming the generated types.
4. **Database: Postgres** (schema in `database/schema.sql`), with CHECK constraints and, where it
   helps, row-level security, for defense in depth beyond the app layer.

Rationale: keeps Roshan's LLM/RAG work in Python's strongest ecosystem and reuses the existing
agent; gives one backend language for a small team; Pydantic enforces validation at trust
boundaries; auditability comes from typed models plus DB constraints plus the append-only audit
table, not from an exotic type system the team cannot maintain.

## Consequences
Positive: one backend language; reuse the Python agent; best-in-class RAG/LLM libraries; typed
request/response boundaries; contract drift between backend and Velo becomes impossible; runs cheap
(a container on a free tier, and the batch collection stays a free GitHub Actions job).

Negative / mitigations:
- Python is dynamically typed. Mitigate with Pydantic models at every boundary, an enum-backed run
  state machine, and Postgres CHECK constraints. Compile-time proof (Rust/F#) is stronger but not
  worth the team cost here.
- Python hosting/perf is heavier than a compiled binary. Mitigate with a small container on a
  free tier; the heavy scheduled work is already a GitHub Actions job with no always-on server.

## Alternatives considered (and why not)
- **Go (single static binary, sqlc):** cheaper to host and compiled-safe, but adds a second backend
  language and a learning curve for marginal gain now. Revisit only if hosting cost or performance
  ever demands it.
- **TypeScript / Deno everywhere:** one language across front and back, but it discards the working
  Python agent and Python's mature LLM ecosystem. Wasted rewrite, weaker tools.
- **Rust typestate / F# / Gleam / Elixir / Ada-SPARK:** can make illegal state transitions a
  compile error and are genuinely elegant for a fail-closed control core. Rejected for this team
  and timeline: a three-person placement team cannot learn, ship, and maintain them in weeks
  without a bus-factor of one.
- **Postgres-as-backend (PostgREST + RLS + triggers):** removes most app code, but hides the
  approval/audit logic in SQL and policies that a junior team finds hard to audit and debug. We
  still adopt the useful half (constraints, RLS) without making the DB the whole application.

## Escape hatch
If the fail-closed state machine or source-verification rules ever must be provably identical in
both the backend and Velo, write that kernel once in Rust, compile to WASM, and run the same
bytecode on both sides. Overkill now; recorded so the option is not forgotten.
