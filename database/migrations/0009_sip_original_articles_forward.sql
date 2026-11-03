-- 0009: forward-only upgrade for original collector article evidence (#531).
--
-- Databases that already applied 0008 must retain the exact applied 0008
-- checksum. An ALTER in this new migration upgrades them instead of silently
-- relying on CREATE TABLE IF NOT EXISTS to add a missing column.
--
-- Pre-existing 0008 evidence rows cannot be trusted as original-body proof.
-- Do not manufacture the missing source articles, alter append-only records
-- or treat NULL as successful migration. Old rows remain readable but unusable
-- by the disabled importer; new evidence requires independently authorised
-- staging on a *new run* after original capture verification.
alter table sip_import_evidence
  add column if not exists raw_articles jsonb;

-- NOT VALID deliberately skips existing legacy rows. PostgreSQL still
-- enforces this constraint on every future INSERT/UPDATE. The importer
-- separately rejects NULL original article evidence for legacy rows.
-- No UPDATE/backfill of append-only old records is authorised.
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'sip_import_evidence'::regclass
      and conname = 'sip_import_evidence_raw_articles_new_required'
  ) then
    alter table sip_import_evidence
      add constraint sip_import_evidence_raw_articles_new_required
      check (
        raw_articles is not null
        and case when jsonb_typeof(raw_articles) = 'array'
          then jsonb_array_length(raw_articles) between 1 and 5000
          else false end
      ) not valid;
  end if;
end;
$$;
