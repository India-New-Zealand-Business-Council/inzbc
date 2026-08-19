# Module — AI Communications Assistant

Owner: Roshan (service) / Paras (UI) · Status: service side building, UI not started · Staff-only,
adversarially tested before use.

## Purpose
Staff drafting helper for newsletters, event announcements, LinkedIn posts, member spotlights.
Produces **drafts only**; a named human approves before anything is sent or published.

## Controls (AI governance, brief §13)
Approved voice/style guidance, channel rules (email/website/social), stakeholder sensitivity rules,
prohibited topics + data, approval matrix, approved templates, test scenarios, publication/send
controls (blocked by default), record-keeping.

## Prohibited by default
No member/sponsor/stakeholder personal data; no confidential government/commercial data; no external
send or publish; no training on INZBC data; no autonomous action through connected accounts.

## Must pass before staff use
Adversarial/security review: hallucination, bias, privacy, prompt-injection, sensitive-data tests.
This is the explicit security-review step in the placement brief — not skipped.

## Dependencies
Bhanu's auth/audit; INZBC voice guide + approved templates; API access for the model.

## Definition of done
Templates + style loaded; prohibited-data tests pass; hallucination/prompt-injection tests pass;
all outputs are drafts; external send/publish blocked by default; review + audit trail tested.

**Status against this list, 14 Aug 2026:**
- All outputs are drafts — **done**. No publish path exists anywhere in this codebase
  (`docs/api-integration-spec.md` Open item #4), so this holds by construction, not by a check
  that could be bypassed.
- External send/publish blocked by default — **done**, for the same reason: there is nothing to
  send through.
- Review + audit trail — **service side done, UI not started.** `POST /api/comms/drafts/{id}/approve`
  persists who approved a draft and refuses the draft's own author (BR8,
  `services/api/comms_persistence.py`); every create and every approval is an audited
  `comms_draft.*` row. `GET /api/comms/drafts` / `/{id}` exist for a reviewer to read against.
  Issue #60 (the actual review screen a reviewer uses) has not been built - what exists is the API
  it depends on, not the reviewer's experience.
- Templates + style loaded — **not done.** `apps/comms/draft.py` builds a deliberately generic
  prompt; the INZBC voice guide is still a named dependency, not wired in.
- Prohibited-data / hallucination / prompt-injection tests — **not done as a comms-specific
  suite.** `ModelGateway`'s redaction and boundary-refusal controls apply to every call including
  this module's (`docs/api-integration-spec.md`'s "structured case" is closed), but the free-text
  brief path (`STAFF_AUTHORED`) has no structural control - see that document's "live gap"
  section and #303.
- Adversarial/security review "before staff use" — **not started**, and cannot start
  meaningfully until the UI exists for a reviewer to actually use.
