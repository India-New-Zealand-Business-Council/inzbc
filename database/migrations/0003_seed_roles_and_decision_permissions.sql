-- 0003: seed `roles` and `decision_role_permissions`, so a decision can be recorded at all (#348).
--
-- Until now neither table had rows outside test fixtures, and `role_seed.py` invents ids with
-- `max(id) + 1`. That is fine for a test and useless as a system of record: nothing said which
-- role a real account holds, and an empty `decision_role_permissions` means every decision kind
-- is refused. That refusal is correct fail-closed behaviour, which is why
-- `services/api/decisions.py` was never mounted on the HTTP surface.
--
-- **Everything below keys on role NAME, never on id.** An earlier draft of this migration
-- assigned fixed ids and upserted on conflict of id. Run against a database where fixtures had
-- already created roles at other ids, that renames existing roles in place: the demo database has
-- 'SIP Owner' at id 1 with 1,792 `user_roles` rows pointing at it, all of which would silently
-- have become 'Analyst'. Ids are an implementation detail of whichever database got there first;
-- the name is the thing that means something.
--
-- **The permission mapping is an assumption, not a client instruction.** SIP-050 section 26 and
-- ADR-0005 both require report approval and distribution authority to be separate decisions, and
-- neither names the role holding each. Sunil is to confirm this. It is data, so a change is an
-- update rather than a migration, and `enabled = false` retires a grant without deleting the
-- record that it existed.
--
-- This table grants *capability*, not separation. Separation of duties is enforced in
-- `decisions.py`, by refusing a decision from whoever authored the report version being decided
-- on, so granting SIP Owner all three kinds does not let one person approve their own work.

insert into roles (id, name)
select (select coalesce(max(id), 0) from roles) + row_number() over (order by name), name
from (values ('Analyst'), ('Reviewer'), ('SIP Owner'), ('Secretariat'),
             ('Administrator'), ('Board Viewer'), ('Auditor')) as wanted(name)
where not exists (select 1 from roles r where r.name = wanted.name)
on conflict (name) do nothing;

-- CEO Ruling is the SIP Owner's alone: SIP-050 section 26 treats it as the run-level ruling.
-- Report Approval adds Reviewer, the role the SOP puts the QA check on.
-- Distribution Authority adds Secretariat, who operates the send, and stays separate from Report
-- Approval so that "do not infer public authority from internal approval" holds.
insert into decision_role_permissions (kind, actor_role_id, enabled)
select grant_spec.kind::decision_kind, r.id, true
from (values ('CEO Ruling', 'SIP Owner'),
             ('Report Approval', 'SIP Owner'),
             ('Report Approval', 'Reviewer'),
             ('Distribution Authority', 'SIP Owner'),
             ('Distribution Authority', 'Secretariat')) as grant_spec(kind, role_name)
join roles r on r.name = grant_spec.role_name
on conflict (kind, actor_role_id) do update set enabled = excluded.enabled;
