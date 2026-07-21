# Module — AI Communications Assistant

Owner: Roshan (service) / Paras (UI) · Status: planned · Staff-only, adversarially tested before use.

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
