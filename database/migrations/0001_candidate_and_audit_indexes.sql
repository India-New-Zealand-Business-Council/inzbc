-- 0001: hot-path indexes for candidate reads and audit-trail lookup (#334).
--
-- These three are also present in database/schema.sql, so a database built fresh from the
-- baseline already has them. This migration exists for databases baselined before #334 landed -
-- `if not exists` makes it a no-op on the former and the actual change on the latter.
--
-- Measured at 200 runs / 50,000 candidates / 40,000 audit rows by scripts/bench_indexes.py:
--   candidates where run_id = ?                          2.47ms seq scan -> 0.06ms index scan
--   candidates where run_id = ? group by verification    2.08ms seq scan -> 0.08ms index scan
--   audit_log where record_type/record_id order by at    3.33ms seq scan -> 0.07ms index scan
--
-- Not created concurrently. CREATE INDEX takes a write lock for the duration, which on a table
-- with real volume would block writes; CREATE INDEX CONCURRENTLY avoids that but cannot run
-- inside a transaction, and this runner puts every migration in one deliberately. No production
-- database exists yet (#99), so there is nothing to block. Revisit before the first deploy.

create index if not exists candidates_run_id_idx
  on candidates (run_id);

create index if not exists candidates_run_verification_idx
  on candidates (run_id, verification);

create index if not exists audit_log_record_idx
  on audit_log (record_type, record_id, at desc);
