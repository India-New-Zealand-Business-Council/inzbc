-- 0005: Wix-to-internal site-forms webhook submissions (#45).
--
-- Stores validated form submissions delivered from the public Wix Vibe site (`inzview`) to
-- `POST /api/webhooks/wix/site-forms`. Append-only by trigger (`reject_evidence_change`) so a
-- received submission cannot be silently altered or wiped after receipt, and deduplicated on
-- `event_id` with a SHA-256 payload digest check so Wix webhook retries are idempotent.

do $$
begin
  if not exists (select 1 from pg_type where typname = 'site_form_type') then
    create type site_form_type as enum (
      'general_enquiry',
      'membership_enquiry',
      'event_registration',
      'trade_enquiry',
      'partnership_enquiry'
    );
  end if;
end
$$;

create table if not exists site_form_submissions (
  id              uuid primary key default gen_random_uuid(),
  event_id        uuid not null unique,
  form_type       site_form_type not null,
  submitted_at    timestamptz not null,
  received_at     timestamptz not null default now(),
  page_slug       text not null check (btrim(page_slug) <> ''),
  contact_name    text not null check (btrim(contact_name) <> ''),
  contact_email   text not null check (btrim(contact_email) <> '' and position('@' in contact_email) > 1),
  organisation    text,
  phone           text,
  subject         text,
  message         text,
  metadata        jsonb not null default '{}'::jsonb
                    check (jsonb_typeof(metadata) = 'object'),
  payload_sha256  text not null check (btrim(payload_sha256) <> '')
);

create index if not exists site_form_submissions_type_received_idx
  on site_form_submissions (form_type, received_at desc);

drop trigger if exists site_form_submissions_append_only on site_form_submissions;
create trigger site_form_submissions_append_only before update or delete on site_form_submissions
  for each row execute function reject_evidence_change();

drop trigger if exists site_form_submissions_no_wipe on site_form_submissions;
create trigger site_form_submissions_no_wipe before truncate on site_form_submissions
  for each statement execute function reject_evidence_change();
