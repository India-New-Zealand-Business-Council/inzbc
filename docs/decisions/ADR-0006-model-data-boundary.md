# ADR-0006: External model data boundary and redaction policy

**Status:** Approved
**Date:** 2026-08-07
**Decision owner:** INZBC, exercised under delegated decision authority by the technical lead

## Context

INZBC's platform requires member, Board and confidential information to be kept out of external model payloads. The existing redaction mechanism is fail-closed and masks formatted identifiers, but regex redaction cannot reliably detect names, employers, job titles, Board deliberations or other sensitive meaning carried in ordinary prose.

A publication-review gate cannot prevent disclosure to a model provider because that disclosure has already occurred by the time output is reviewed.

## Decision

INZBC adopts **data minimisation and boundary refusal as the primary control**, with regex redaction as defense-in-depth.

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
- free-text notes or correspondence originating from member/CRM records unless an approved transformation has first removed identifiable and confidential content.

A field being absent from this list does not make it safe when its combination with other fields can reasonably identify a person or reveal confidential information.

### 2. Structured data must be minimised before prompt assembly

Callers that construct prompts from structured records MUST use an explicit allowlist of fields needed for the model task. Prohibited fields are dropped before text assembly. Do not assemble a full record and depend on regex to remove sensitive fields afterwards.

For trade-intelligence tasks, preferred external-model inputs are public-source content and non-identifying facts such as source URL, publication date, sector, HS code, tariff/rule text, public statistics and public-government statements.

### 3. Free text is refused by default when its provenance is sensitive

Raw member records, CRM notes, Board material, private email/message bodies and similar free text MUST NOT be passed to an external model merely because the redaction policy is configured.

A future workflow may permit such text only after a separately reviewed transformation demonstrates that the resulting payload contains no personal or confidential information required for the task.

### 4. Regex redaction remains mandatory defense-in-depth

Every external model call continues through `ModelGateway` and the configured redaction policy. Redaction catches formatted identifiers and secrets that accidentally remain after minimisation. A configured policy does not grant permission to send prohibited data.

### 5. Policy approval

`config/redaction-policy.json` is the approved regex policy for formatted identifiers and secrets. Production must set `REDACTION_POLICY_PATH` to that file (or an operationally equivalent mounted copy).

Policy changes require repository review, representative positive and negative tests, and an auditable approval record. No real member data may be placed in policy examples or tests.

### 6. Provider/privacy review remains required

Before a workflow intentionally processes personal information through a third-party AI service, INZBC must document the purpose, necessity, provider handling/retention/training terms, access controls and applicable Privacy Act obligations. This ADR does not treat an external AI provider as automatically authorised to receive personal data.

## Consequences

- Issue #223 becomes the implementation task for enforcing this boundary in code.
- Issue #37's regex mechanism remains valid but is not, by itself, proof that member/Board/confidential data is safe to send.
- #53 and #65 may proceed once their prompt assembly paths enforce this ADR and the approved regex policy is configured.
- Any ambiguity fails closed: omit/refuse the sensitive input rather than infer permission.
