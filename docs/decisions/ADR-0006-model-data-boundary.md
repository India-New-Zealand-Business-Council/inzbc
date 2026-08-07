# ADR-0006: External model data boundary and redaction policy

**Status:** Proposed — direction agreed, approval pending the two gates in §7
**Date:** 2026-08-07
**Decision owner:** INZBC

## Context

INZBC's platform requires member, Board and confidential information to be kept out of external
model payloads. The existing redaction mechanism is fail-closed and masks formatted identifiers,
but regex redaction cannot reliably detect names, employers, job titles, Board deliberations or
other sensitive meaning carried in ordinary prose.

Independent benchmarking puts regex-only PII recall at roughly 0.65 against about 0.96 for a
hybrid regex + NER pipeline, so a regex-only control misses on the order of a third of what it
targets. That is the measured form of the limit `docs/redaction-policy.md` already describes in
prose. It is the reason redaction cannot be the primary control.

A publication-review gate cannot prevent disclosure to a model provider, because that disclosure
has already occurred by the time output is reviewed.

## Decision

INZBC adopts **data minimisation and boundary refusal as the primary control**, with regex
redaction as defense-in-depth.

### 1. Prohibited external-model inputs

The following MUST NOT be sent to an external model in identifiable form:

- member or prospective-member names;
- personal email addresses, phone numbers, postal/street addresses and profile URLs;
- member identifiers and account identifiers;
- job titles tied to an identifiable person;
- employer/organisation names when tied to an identifiable member or private contact;
- passport, visa/immigration, tax, banking, payment-card or date-of-birth data;
- credentials, secrets or authentication material;
- non-public Board papers, minutes, deliberations, votes or attributed comments;
- non-public commercial terms, negotiations or correspondence;
- unpublished intelligence whose source or wording identifies a confidential contributor;
- free-text notes or correspondence originating from member/CRM records unless an approved
  transformation has first removed identifiable and confidential content.

A field being absent from this list does not make it safe when its combination with other fields
can reasonably identify a person or reveal confidential information.

### 2. Structured data must be minimised before prompt assembly

Callers that construct prompts from structured records MUST use an explicit allowlist of fields
needed for the model task. Prohibited fields are dropped before text assembly. Do not assemble a
full record and depend on regex to remove sensitive fields afterwards.

For trade-intelligence tasks, preferred external-model inputs are public-source content and
non-identifying facts such as source URL, publication date, sector, HS code, tariff/rule text,
public statistics and public-government statements.

### 3. Free text is refused by default when its provenance is sensitive

Raw member records, CRM notes, Board material, private email/message bodies and similar free text
MUST NOT be passed to an external model merely because the redaction policy is configured.

A future workflow may permit such text only after a separately reviewed transformation
demonstrates that the resulting payload contains no personal or confidential information beyond
what the task requires.

### 4. Regex redaction remains mandatory defense-in-depth

Every external model call continues through `ModelGateway` and the configured redaction policy.
Redaction catches formatted identifiers and secrets that accidentally remain after minimisation.
A configured policy does not grant permission to send prohibited data.

Within the policy, values are masked by default so the prompt stays coherent, and dropped where
the value adds nothing to the model's understanding — member identifiers, bank accounts, payment
cards, IRD and GSTIN numbers. Dropping is expressed today by an empty replacement string and needs
no code change.

Policy changes require repository review, representative positive and negative tests, and an
auditable approval record. Authorship is confined to whoever holds production configuration: a bad
rule can hang a worker, and the 200,000-character payload cap bounds the input without making the
rule safe. No real member data may appear in policy examples or tests.

### 5. Behaviour when minimisation leaves little intact

Where redaction or minimisation removes the substance of a payload, the call is refused rather
than sent hollowed out. This is not yet implemented: `GatewayResult.redaction_counts` records
which rules fired and how often, but nothing consumes it, so today a gutted prompt is sent exactly
like one that lost a single phone number. The threshold is INZBC's to set and the enforcement is
engineering work; both are tracked with #223.

### 6. Provider and privacy review remains required

Before a workflow intentionally processes personal information through a third-party AI service,
INZBC must document the purpose, necessity, provider handling/retention/training terms, access
controls and applicable Privacy Act 2020 obligations. That work is issue **#113** (preliminary
privacy and data-flow assessment), which is open and unstarted; **#132** is its final counterpart.

This matters beyond internal process. Placing personal information into an AI tool is a
disclosure to the provider under IPP 12, requiring comparable safeguards, a contract, or express
informed consent. The cloud-provider exemption covers an agent that does not use the data for its
own purposes, which is a question about the provider's terms and has not been checked. The
Privacy Commissioner's published expectations for agencies using AI include senior leadership
approval and a Privacy Impact Assessment carried out *before* deployment.

This ADR does not treat an external AI provider as automatically authorised to receive personal
data.

### 7. What approval still requires

The direction in §§1–6 is settled. Two gates remain before this ADR moves to Approved, and
neither is satisfied today.

**The approved policy file does not exist.** Only `config/redaction-policy.proposed.json` is in
the repository. Approval means copying it to `config/redaction-policy.json`, reviewing what is
missing from its eighteen rules — a question only INZBC can answer, since it knows its own data —
and setting `REDACTION_POLICY_PATH` to that file in production. Until the copy exists, any
instruction to point production at it is unexecutable, and the gateway will refuse every model
call. That refusal is correct behaviour, not a fault.

**The delegation is unrecorded.** Bhanu stated on 7 August 2026 that Sunil delegated decision
authority to him. That is recorded as stated, not verified: the convention elsewhere in this repo
is that Sunil's authority is exercised in writing, and no instrument is on file. One email from
Sunil naming the scope, filed against #37, closes this. Delegation moves who signs inside INZBC;
under the Privacy Act 2020, INZBC remains the agency regardless.

## Consequences

- Issue **#223** becomes the implementation task for enforcing this boundary in code, including
  the §5 threshold.
- Issue **#37**'s regex mechanism remains valid but is not, by itself, proof that member, Board or
  confidential data is safe to send.
- **#53** and **#65** may proceed once their prompt assembly paths enforce this ADR and the
  approved regex policy is configured. Service-side development may begin now against a fake
  gateway; it is deployment that waits.
- Any ambiguity fails closed: omit or refuse the sensitive input rather than infer permission.

## Sources

- OWASP Top 10 for LLM Applications 2025, LLM02 Sensitive Information Disclosure —
  https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Office of the Privacy Commissioner, Artificial Intelligence and the Information Privacy
  Principles — https://www.privacy.org.nz/resources-and-learning/a-z-topics/ai/
- Office of the Privacy Commissioner, Sending information overseas (IPP 12) —
  https://www.privacy.org.nz/responsibilities/disclosing-personal-information-outside-new-zealand/
- Microsoft Presidio, hybrid regex + NER reference implementation —
  https://microsoft.github.io/presidio/
