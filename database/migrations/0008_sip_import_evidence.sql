-- 0008: Inert, server-held SIP capture/import evidence and atomic import claim (#528).
-- The application has NO route to stage capture or execute an import. An authorised
-- staging process, separate from the request path, must verify and persist the
-- original capture, its SHA-256 and resolved candidate batch before any import.
-- This schema is not production-import permission.
create table if not exists sip_import_evidence (
  run_id             uuid primary key references runs(id),
  articles_sha256    text not null check (articles_sha256 ~ '^[0-9a-f]{64}$'),
  batch_payload      jsonb not null check (jsonb_typeof(batch_payload) = 'object'),
  source_count       integer not null check (source_count = 112),
  evidence_ref       text not null check (btrim(evidence_ref) <> ''),
  staged_by          uuid not null references users(id),
  staged_at          timestamptz not null default now()
);
create table if not exists sip_import_claims (
  run_id             uuid primary key references runs(id),
  claim_key          text not null check (claim_key ~ '^[0-9a-f]{64}$'),
  articles_sha256    text not null check (articles_sha256 ~ '^[0-9a-f]{64}$'),
  candidate_count    integer not null check (candidate_count between 1 and 5000),
  actor_id           uuid not null references users(id),
  committed_at       timestamptz not null default now()
);
drop trigger if exists sip_import_evidence_append_only on sip_import_evidence;
create trigger sip_import_evidence_append_only before update or delete on sip_import_evidence
  for each row execute function reject_evidence_change();
drop trigger if exists sip_import_evidence_no_wipe on sip_import_evidence;
create trigger sip_import_evidence_no_wipe before truncate on sip_import_evidence
  for each statement execute function reject_evidence_change();
drop trigger if exists sip_import_claims_append_only on sip_import_claims;
create trigger sip_import_claims_append_only before update or delete on sip_import_claims
  for each row execute function reject_evidence_change();
drop trigger if exists sip_import_claims_no_wipe on sip_import_claims;
create trigger sip_import_claims_no_wipe before truncate on sip_import_claims
  for each statement execute function reject_evidence_change();
