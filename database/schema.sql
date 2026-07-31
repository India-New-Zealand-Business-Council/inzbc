-- SIP database schema — v0.1 draft (Postgres)
-- Grounded in the Intelligence Database v1.9 model and the SIP spec (docs/sip/).
-- Contract for Roshan (pipeline) and Paras (UI) to build against. Not yet migrated;
-- the internal-platform decision (AIOS foundation decision 2) may host this differently,
-- but the shape stands. The Intelligence Database is the single Action Register.

-- ---------- controlled vocab (from the workbook's Lookup Values) ----------
create type signal_strength   as enum ('Low','Medium','High','Critical');
create type source_confidence as enum ('High','Medium','Low','Unverified');
create type source_outcome    as enum ('Included','Context','Suppressed','Inaccessible','Excluded','No Qualifying Item');
create type verification_state as enum ('Verified','Partially Verified','Unverified','Not Required','Rejected');
create type approval_state     as enum ('Pending','Approved','Rejected','Returned for Correction','Superseded');
create type distribution_state as enum ('Not Authorised','Internal Approved','Member Approved','Public Approved','Distributed','Withdrawn');
create type run_state          as enum (
  'Draft','Run Authorised','Coverage Locked','Scanning','Candidate Review','Report Drafted',
  'QA In Progress','QA Failed','Awaiting CEO Decision','Continue','Continue With Correction',
  'Paused','Stopped','Approved for Manual Distribution','Distributed','Closed','Corrected','Withdrawn'
);

-- ---------- identity ----------
create table roles (
  id   smallint primary key,
  name text not null unique  -- SIP Owner, Analyst, Reviewer, Secretariat, Administrator, Board Viewer, Auditor
);

create table users (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  email         text not null unique,
  role_id       smallint not null references roles(id),
  active        boolean not null default true,
  mfa_enabled   boolean not null default false,
  created_at    timestamptz not null default now(),
  last_login_at timestamptz
);

-- ---------- production run ----------
create table runs (
  id                    uuid primary key default gen_random_uuid(),
  run_number            text not null unique,          -- RUN-YYYYMMDD-01
  coverage_start_utc    timestamptz not null,
  coverage_end_utc      timestamptz not null,
  coverage_timezone     text not null default 'Pacific/Auckland',
  state                 run_state not null default 'Draft',
  prompt_version        text not null,                 -- e.g. SIP-050 v1.1
  production_enabled    boolean not null default false,
  initiated_by          uuid not null references users(id),
  analyst_id            uuid references users(id),
  reviewer_id           uuid references users(id),      -- must differ from analyst (enforced in app)
  started_at            timestamptz,
  completed_at          timestamptz,
  qa_status             text,
  -- Optimistic concurrency (#117): every state transition does
  -- `UPDATE ... SET version = version + 1 WHERE id = ? AND version = ?`. Zero rows affected means
  -- someone else's transition landed first - the caller must re-read and retry, not silently
  -- overwrite. Two reviewers acting on the same run at once must not both be able to commit.
  version               integer not null default 0,
  created_at            timestamptz not null default now(),
  check (coverage_end_utc > coverage_start_utc),
  check (analyst_id is null or reviewer_id is null or analyst_id <> reviewer_id)
);

-- ---------- source coverage ----------
create table source_library (
  id            uuid primary key default gen_random_uuid(),
  sip185_code   text unique,              -- SIP-185 register id, e.g. 'NZ-OFF-001'; stable, unique.
                                          -- Nullable so an ad-hoc/non-register source can exist,
                                          -- but every SIP-185-backed source MUST carry it at seed
                                          -- time: source-check recording resolves by this code and
                                          -- hard-fails without it (source_register.record_source_outcome).
  name          text not null,            -- display / candidate-capture label only; NOT unique
                                          -- (NZ and India both have a 'Ministry of Defence' and a
                                          -- 'Ministry of Education') - never resolve a source-check by name.
  layer         smallint not null,        -- 1 Official .. 5 Other
  mandatory     boolean not null default false,
  base_url      text,
  fallback_note text,
  active        boolean not null default true
);

create table source_checks (
  id           uuid primary key default gen_random_uuid(),
  run_id       uuid not null references runs(id) on delete cascade,
  source_id    uuid not null references source_library(id),
  checked_at   timestamptz not null default now(),
  method       text,
  outcome      source_outcome not null,
  fallback_used boolean not null default false,
  access_error text,
  notes        text,
  unique (run_id, source_id)
);

-- ---------- candidate + finalised intelligence ----------
create table candidates (
  id                 uuid primary key default gen_random_uuid(),
  run_id             uuid not null references runs(id) on delete cascade,
  source_id          uuid references source_library(id),
  url                text,
  headline           text not null,
  summary            text,
  published_at       timestamptz,
  captured_at        timestamptz not null default now(),
  in_coverage_window boolean,
  nz_relevance       smallint,   -- 0..5 scores
  india_relevance    smallint,
  member_relevance   smallint,
  signal             signal_strength,
  confidence         source_confidence,
  verification       verification_state not null default 'Unverified',
  duplicate_of       uuid references candidates(id),
  included           boolean,
  reason             text,
  proposed_routing   text
);

create table daily_intelligence (
  id             uuid primary key default gen_random_uuid(),
  run_id         uuid not null references runs(id) on delete cascade,
  candidate_id   uuid references candidates(id),
  rank           smallint,
  headline       text not null,
  what_happened  text,
  why_it_matters text,
  nz_impact      text,
  member_impact  text,
  ceo_action     text,
  member_action  text,
  signal         signal_strength,
  confidence     source_confidence,
  approval       approval_state not null default 'Pending'
);

-- ---------- registers (Intelligence Database is the authority) ----------
create table action_register (
  id             uuid primary key default gen_random_uuid(),
  action_code    text not null unique,      -- ACT-016 ...
  title          text not null,
  description    text,
  owner_id       uuid references users(id),
  owner_text     text,
  priority       text,
  due_date       date,
  review_date    date,
  status         text not null,             -- Open, Closed, Controlled Monitoring, ...
  evidence_ref   text,
  closed_at      timestamptz,
  created_at     timestamptz not null default now()
);

create table watch_lists (
  id            uuid primary key default gen_random_uuid(),
  watch_code    text not null unique,       -- WL-006 ...
  title         text not null,
  category      text,
  frequency     text,
  escalation    text,
  status        text not null,
  next_review   date
);

create table exceptions (
  id            uuid primary key default gen_random_uuid(),
  run_id        uuid references runs(id),
  exception_type text not null,
  severity      text not null,
  owner_id      uuid references users(id),
  status        text not null,
  original_preserved boolean not null default true,
  correction_ref text,
  created_at    timestamptz not null default now()
);

create table approvals (
  id                 uuid primary key default gen_random_uuid(),
  run_id             uuid not null references runs(id),
  report_version     text not null,
  ceo_decision       text,                  -- Continue / Continue with Correction / Pause / Stop
  approval           approval_state not null default 'Pending',
  distribution       distribution_state not null default 'Not Authorised',
  approver_id        uuid references users(id),
  decided_at         timestamptz,
  recipient          text,
  sent_at            timestamptz,
  delivery_result    text
);

-- ---------- append-only audit ----------
create table audit_log (
  id           bigserial primary key,
  at           timestamptz not null default now(),
  user_id      uuid references users(id),
  action       text not null,
  record_type  text,
  record_id    text,
  old_value    text,
  new_value    text,
  reason       text,
  approval_ref text
);
