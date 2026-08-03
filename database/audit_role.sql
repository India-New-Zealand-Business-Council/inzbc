-- Append-only privileges for audit_log (#118). Applied separately from schema.sql because the
-- application login role is deployment-specific and does not exist when CI applies the schema (see
-- the grants note in schema.sql). This grant is the *real* append-only boundary: the
-- audit_log_append_only trigger in schema.sql only catches a mistake by a role that could otherwise
-- UPDATE/DELETE (a migration, or the table owner re-granting itself). A trail the app role could
-- rewrite or erase is not an audit trail, so the app role never gets UPDATE, DELETE or TRUNCATE.
--
-- Run against a database that already has schema.sql applied, naming the app login role:
--   psql "$DATABASE_URL" -v app_role=inzbc_app -f database/audit_role.sql
-- Defaults to 'inzbc_app' when -v app_role is not supplied. The role must already exist.

\if :{?app_role}
\else
  \set app_role inzbc_app
\endif

-- INSERT + SELECT only, and USAGE on the bigserial id sequence so an INSERT can allocate an id.
revoke all on table audit_log from :app_role;
grant insert, select on table audit_log to :app_role;
grant usage, select on sequence audit_log_id_seq to :app_role;
