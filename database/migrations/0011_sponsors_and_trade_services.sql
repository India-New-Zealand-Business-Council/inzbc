-- Sponsors and Trade Services (#200): sponsor pipeline, append-only benefit delivery evidence,
-- trade-service requests, and confidentiality/dual-consent gated introductions.

create table if not exists sponsors (
  id               uuid primary key default gen_random_uuid(),
  name             text not null check (btrim(name) <> ''),
  tier             text not null check (btrim(tier) <> ''),
  stage            text not null
                     check (stage in ('prospect', 'proposal', 'active', 'renewal', 'lapsed')),
  owner_id         uuid references users(id),
  owner_text       text,
  annual_value_nzd integer check (annual_value_nzd is null or annual_value_nzd >= 0),
  renewal_date     date,
  notes            text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  check (owner_id is not null or btrim(coalesce(owner_text, '')) <> '')
);

create table if not exists sponsor_benefit_deliveries (
  id               uuid primary key default gen_random_uuid(),
  sponsor_id       uuid not null references sponsors(id),
  benefit_title    text not null check (btrim(benefit_title) <> ''),
  promised_summary text not null check (btrim(promised_summary) <> ''),
  evidence_ref     text not null check (btrim(evidence_ref) <> ''),
  delivered_at     timestamptz not null,
  recorded_by      uuid not null references users(id),
  created_at       timestamptz not null default now()
);

create index if not exists sponsor_benefit_deliveries_sponsor_idx
  on sponsor_benefit_deliveries (sponsor_id, delivered_at desc);

drop trigger if exists sponsor_benefit_deliveries_append_only on sponsor_benefit_deliveries;
create trigger sponsor_benefit_deliveries_append_only
  before update or delete on sponsor_benefit_deliveries
  for each row execute function reject_evidence_change();

drop trigger if exists sponsor_benefit_deliveries_no_wipe on sponsor_benefit_deliveries;
create trigger sponsor_benefit_deliveries_no_wipe
  before truncate on sponsor_benefit_deliveries
  for each statement execute function reject_evidence_change();

create table if not exists trade_service_requests (
  id              uuid primary key default gen_random_uuid(),
  requester_org   text not null check (btrim(requester_org) <> ''),
  corridor        text not null check (btrim(corridor) <> ''),
  service_type    text not null check (btrim(service_type) <> ''),
  summary         text not null check (btrim(summary) <> ''),
  status          text not null check (status in ('open', 'in_progress', 'fulfilled', 'declined')),
  confidentiality text not null check (confidentiality in ('internal', 'restricted', 'board_only')),
  owner_text      text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create table if not exists trade_introductions (
  id              uuid primary key default gen_random_uuid(),
  sponsor_id      uuid references sponsors(id),
  request_id      uuid references trade_service_requests(id),
  party_a_org     text not null check (btrim(party_a_org) <> ''),
  party_b_org     text not null check (btrim(party_b_org) <> ''),
  purpose         text not null check (btrim(purpose) <> ''),
  consent_party_a boolean not null default false,
  consent_party_b boolean not null default false,
  confidentiality text not null check (confidentiality in ('internal', 'restricted', 'board_only')),
  status          text not null
                    check (status in ('proposed', 'consented', 'introduced', 'declined')),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  check (status <> 'introduced' or (consent_party_a and consent_party_b))
);

create index if not exists trade_introductions_status_idx
  on trade_introductions (status, created_at desc);
