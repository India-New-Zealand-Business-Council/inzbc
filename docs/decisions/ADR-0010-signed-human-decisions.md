# ADR-0010: Bind human decisions to their authors with server-held HMAC signatures

**Status:** Accepted, 24 Oct 2026. Implemented in #448.
**Decision owner:** Bhanu Gupta, tech lead.
**Studio 6 objective:** 1.1 (choosing between options with evidence).
**Number:** 0009 was used by the closed, unmerged proposal in #401, so this record takes 0010.

## Context

The replay baseline in [agent-safety-baseline.md](../research/agent-safety-baseline.md) found one
safety-relevant gap. The coordinator agent cannot cross a human gate: 48 of 48 attempts were
blocked. But the audit artefact could be forged. A transition carrying a `HumanDecision` replayed
as valid in 0 of 200 forgery attempts detected, because a decision recorded *that* someone approved
and nothing proved *who* did. Edits to metadata were not detected either (0 of 1000).

In the deployed system that attacker is held off by the database, not by the log itself.
`audit_log` grants the application role INSERT and SELECT only, and a trigger backs that up. The
question was whether that is enough, and if not, which change to make in W6.

## Options considered

| | A. Database privileges only (status quo) | B. HMAC signatures under one server-held key (chosen) | C. Per-approver asymmetric signatures | D. External append-only ledger service |
|---|---|---|---|---|
| Detects a forged decision on replay | No: 0/200 measured | Yes: 200/200 measured | Yes | Yes, for rows written through it |
| Detects metadata edits | No: 0/1000 measured | Yes, with the hash-chained seal: 1000/1000 measured | Only for the signed fields | Yes |
| Protects against someone with INSERT on `audit_log` | No | Yes, unless they also hold the key | Yes | Yes |
| Proves *which person* approved, to a third party | No | No. The server vouches, so anyone with the key could sign | Yes. Each approver holds their own key | No. It proves the order, not the author |
| New infrastructure | None | One environment secret | A key per approver, issuing and revocation, client-side signing in the browser | A new hosted service, account and client |
| Fits this block (part-time team, 9 weeks, client approval needed for new services) | Yes | Yes. Built and measured in a day | No. Key issuing for INZBC staff needs the client, and the browser signing flow would need its own security review | No. A new hosted service with client data is a client decision |
| Backward compatible with existing rows | Yes | Yes. Unsigned legacy rows replay until `SIP_REQUIRE_SIGNED_DECISIONS` is turned on | Needs a migration path | Needs a migration path |

## Decision

**Option B.**
- **Signing.** `RunRepository.apply_transition` signs every gated transition with HMAC-SHA256 under
  `SIP_DECISION_SIGNING_KEY` when a person records it.
- **Sealing.** The agent's audit log is folded into a SHA-256 hash chain, and the chain head is
  MACed with the same key.
- **Verification on replay.** Replay refuses:
  - a decision whose signature does not verify
  - a seal that is missing or wrong
  - unsigned gated rows, once signatures are required

This follows Schneier and Kelsey (1999), cited in the
[literature review](../research/agent-safety-literature-review.md).

**Why not A.** It leaves the measured gap open. It also makes the guarantee depend on a grant that
lives outside the repository (`database/audit_role.sql` is applied per deployment), which is easy
to get wrong.

**Why not C, even though it is stronger.** C is the only option that proves to an outsider which
person approved. But it needs INZBC to issue and revoke a key for each approver, and a signing
flow in the browser. Neither fits this block, and the first is the client's decision.

B closes the gap the research question is about: whether an automated component, or anyone who can
only write rows, can make a gate look crossed. C is recorded as the next step if INZBC ever needs
proof of authorship that does not rest on trusting the server.

**Why not D.** D proves the order of entries, not who made the decision. It also adds a hosted
service holding client data, which is the client's call.

## Consequences

- **The key becomes the thing to protect.** Anyone holding it can forge, so it is held only by the
  server and listed in the [secrets register](../secrets-register.md). It never reaches a model or
  a browser.
- **Rotating the key needs a plan.** Rows signed with the old key stop verifying, so rotation has
  to re-verify existing rows before the old key is dropped.
- **Legacy rows still replay.** Rows written before the change replay unsigned until
  `SIP_REQUIRE_SIGNED_DECISIONS` is turned on. Turning it on in production is a separate
  configuration decision.
- **The gate result does not change.** Gate safety stays 48/48. The change makes the evidence
  trustworthy; it does not change what the agent can do.

## Evidence

- Before and after table: [agent-safety-baseline.md](../research/agent-safety-baseline.md),
  section 5.
- Code: `apps/sip/core/audit_seal.py`, `services/api/persistence.py`, migration 0006.
- Tests:
  - `apps/sip/core/tests/test_audit_seal.py`
  - `services/api/tests/test_signed_decisions.py`, on real Postgres
  - `apps/sip/core/tests/test_research_eval.py`, which pins both columns
