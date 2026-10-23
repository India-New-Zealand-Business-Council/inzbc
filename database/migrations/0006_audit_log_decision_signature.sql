-- 0006: signed human decisions on gated run transitions (Studio 6 research change, #62).
--
-- The agent-safety baseline (docs/research/agent-safety-baseline.md) found that a forged gated
-- transition carrying an approval replays as valid, because nothing binds a decision to the person
-- who made it. `apply_transition` now stores an HMAC-SHA256 signature (apps/sip/core/audit_seal.py)
-- over the run, the exact transition, the actor, the approval reference and the reason, made with
-- the server-held SIP_DECISION_SIGNING_KEY. `rehydrate` verifies it, so a gated row written or
-- edited without the key is refused.
--
-- Nullable: rows written before this change carry no signature. They stay replayable until
-- SIP_REQUIRE_SIGNED_DECISIONS is turned on, after which an unsigned gated row is refused.

alter table audit_log
  add column if not exists decision_signature text
    check (decision_signature is null or decision_signature ~ '^[0-9a-f]{64}$');
