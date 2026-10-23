-- 0007: Agent rehearsals, the sealed trail of each in-app SIP coordinator run (Studio 6).
--
-- A rehearsal runs the coordinator agent (`apps/sip/core/agent_loop.py`) over a launch-authorised
-- run without changing that run: the persisted run's state, candidates and source checks are
-- untouched, and the agent still stops at the QA human gate. What is kept is the evidence of what
-- the agent proposed: its full audit log as JSON, the SHA-256 chain head over that log, and the
-- HMAC seal over the head when `SIP_DECISION_SIGNING_KEY` is configured. Append-only by trigger,
-- like every other evidence table, so a stored trail cannot be rewritten after the fact.

create table if not exists agent_rehearsals (
  id           uuid primary key default gen_random_uuid(),
  run_id       uuid not null references runs(id),
  started_by   uuid not null references users(id),
  started_at   timestamptz not null default now(),
  outcome      text not null check (outcome in ('reached_qa', 'stopped')),
  stop_reason  text check (outcome = 'reached_qa' or btrim(coalesce(stop_reason, '')) <> ''),
  final_state  text not null check (btrim(final_state) <> ''),
  steps        integer not null check (steps >= 0),
  audit        jsonb not null check (jsonb_typeof(audit) = 'object'),
  chain_head   text not null check (chain_head ~ '^[0-9a-f]{64}$'),
  seal         text check (seal is null or seal ~ '^[0-9a-f]{64}$')
);

create index if not exists agent_rehearsals_run_started_idx
  on agent_rehearsals (run_id, started_at desc);

drop trigger if exists agent_rehearsals_append_only on agent_rehearsals;
create trigger agent_rehearsals_append_only before update or delete on agent_rehearsals
  for each row execute function reject_evidence_change();

drop trigger if exists agent_rehearsals_no_wipe on agent_rehearsals;
create trigger agent_rehearsals_no_wipe before truncate on agent_rehearsals
  for each statement execute function reject_evidence_change();
