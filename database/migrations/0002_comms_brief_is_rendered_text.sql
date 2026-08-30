-- 0002: record that comms_drafts.brief now holds a rendered structured brief (#303).
--
-- No DDL. The column stays `text not null` and every existing row stays valid, because the brief
-- is rendered to text before it is stored - that was the point of rendering rather than storing
-- the structure. This migration exists to leave the change in the ordered record rather than
-- having it visible only in application code.
--
-- What changed is upstream of the database: POST /api/comms/draft no longer accepts a single
-- 4,000-character `brief`. It takes `topic`, `key_points`, `links` and `tone`, each capped, and
-- the API renders them into the text this column has always held.
--
-- Rows written before this change are free-text briefs. They are not distinguishable from rows
-- written after it, and deliberately so: both are "the text that was sent to the model", which is
-- what a reviewer or an incident responder needs. If that distinction ever matters, it needs a
-- new column and a migration that backfills it - not an inference over existing text.
--
-- The residual exposure #303 describes is reduced, not closed. A staff member can still type a
-- member's name into `topic`. The declaration to the model gateway stays STAFF_AUTHORED because
-- that is true; MINIMISED_RECORD would not be.

comment on column comms_drafts.brief is
  'The brief as sent to the model. Since #303 this is rendered from structured fields '
  '(topic, key points, links, tone); rows predating it are free text. Staff-typed either way, '
  'so it may contain anything a staff member entered.';
