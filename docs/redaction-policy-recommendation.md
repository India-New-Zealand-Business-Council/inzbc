# Redaction policy — researched recommendation

**Status: recommendation only. This document approves nothing and nothing loads from it.**
`REDACTION_POLICY_PATH` stays unset, `config/redaction-policy.proposed.json` stays where it is,
and `ModelGateway.complete()` continues to refuse every model call. Written to support a decision,
not to record one.

Companion to [redaction-policy.md](./redaction-policy.md), which describes the mechanism and lists
the decisions INZBC owes. This document researches those decisions and recommends answers.

## Why this exists

Bhanu stated on 7 August 2026 that Sunil has delegated decision authority to him. That is recorded
here as stated, not as verified — the convention elsewhere in this repo (`CLAUDE.md`, on the live
site) is that Sunil's authority is exercised in writing, and no written instrument is on file. If
the delegation is real, the fix is small: one email from Sunil naming its scope, filed against
issue #37. That single artifact makes every decision below signable.

Note that delegation moves who signs inside INZBC. It does not move the obligation. Under the
Privacy Act 2020 INZBC remains the agency, whoever holds the pen.

## What current practice actually does

Three findings, and two of them cut against approving the proposed policy as-is.

**Regex alone is measured at roughly a third of PII missed.** Benchmarks put regex-only recall
around 0.65 against about 0.96 for a hybrid pipeline. Regex dominates on structured identifiers —
cards, emails, phone numbers, tax numbers — and fails outright on contextual entities: person
names, organisations, addresses in prose. The state of practice is not regex or NER but both,
which is what Microsoft Presidio is: regex recognisers over a spaCy NER backend.

This is the same limit `redaction-policy.md` already states in prose ("Delegation lead: Priya
Sharma, Chief Executive, Koru Exports Ltd" passes through untouched). The research puts a number
on it. Approving the eighteen proposed rules as sufficient would be approving a control that
independent benchmarking says leaks about a third of what it is meant to catch.

**OWASP LLM02 treats redaction as one layer of several, not the control.** Its guidance pairs
sanitisation with access control applied *before* data reaches the model and with keeping
sensitive material out of prompts entirely. That maps onto issue #223 — refuse member data at the
boundary rather than mask it afterwards — which is currently open. Redaction is the last line, not
the line.

**The NZ Privacy Commissioner expects a PIA before deployment, not after.** Putting personal
information into an AI tool is a disclosure to the provider under IPP 12, requiring comparable
safeguards, a contract, or express informed consent. The cloud-provider exemption covers an agent
that does not use the data for its own purposes, which is a question about the provider's terms
and has not been checked here. OPC's published expectations for agencies using AI include senior
leadership approval, a Privacy Impact Assessment carried out **before** starting, transparency,
and human review.

No privacy assessment exists in this repository. Issue #113 (preliminary privacy and data-flow
assessment) is open and unstarted; #132 (final assessment) likewise.

## Recommendations

**1. Which categories are confidential.** Recommend treating as confidential: member names and
contact details, Board papers and deliberations, commercial terms, and unpublished intelligence —
the four `redaction-policy.md` already names. The important part is that this answer splits in
two. Formatted identifiers go to the policy; everything carried in prose cannot be redacted at any
accuracy worth relying on and must instead be excluded from the payload (#223). Recommend
recording both halves in the same decision so approval is not mistaken for coverage.

**2. Mask or drop.** Recommend masking as the default, since it preserves prompt coherence, and
dropping for values that add nothing to a model's understanding — member IDs, bank accounts,
payment cards, IRD and GSTIN numbers. This is a configuration choice available today: an empty
replacement string drops rather than masks. No code change.

**3. Payloads that are mostly confidential.** Recommend refusing the call rather than sending a
hollowed-out prompt. This one needs a build: `GatewayResult.redaction_counts` records which rules
fired and how often, but nothing consumes it, so there is no threshold behaviour at all today. A
prompt stripped to nothing is currently sent exactly like one that lost a single phone number.
Recommend a rule expressed as a proportion of the payload redacted, decided by INZBC and enforced
in `ModelGateway.complete()`.

**4. Who owns policy changes.** Recommend confining authorship to whoever holds production
configuration, per `redaction-policy.md`'s existing warning that a bad rule can hang a worker and
that the 200,000-character cap bounds input without making the rule safe. Recommend policy edits
emit an audit event, consistent with how `apply_transition` already audits state changes.

**5. What is missing from the eighteen rules.** Cannot be answered from research. INZBC knows its
own data; the team does not. Left open deliberately rather than filled with an assumption, per
`CLAUDE.md`.

## What this does not unblock

Approving the policy would not enable a live run. `OPENAI_API_KEY` is still not an org secret,
which needs an org admin, and the Comms Assistant still cannot publish without the named reviewer
of issue #96. Those are access and appointment, not decisions, and no delegation resolves them.

The honest sequence is: record the delegation, complete the PIA (#113), decide 1–5, build the
threshold from 3, then approve. Approving ahead of the PIA inverts the order OPC asks for, on a
control that benchmarks say catches about two thirds of what it targets, for an organisation whose
members are the data subjects.

## Decision record

To be completed by the approver. Unsigned until every field is filled.

```
Approved by:
Role and authority:
Delegation instrument (if signing as delegate):
Date:
Decisions 1-5 as recorded above, with any variation:
PIA reference (#113):
Deployment path set in REDACTION_POLICY_PATH:
```

## Sources

- OWASP Top 10 for LLM Applications 2025, LLM02 Sensitive Information Disclosure —
  https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Office of the Privacy Commissioner, Artificial Intelligence and the Information Privacy
  Principles — https://www.privacy.org.nz/resources-and-learning/a-z-topics/ai/
- Office of the Privacy Commissioner, Sending information overseas (IPP 12) —
  https://www.privacy.org.nz/responsibilities/disclosing-personal-information-outside-new-zealand/
- Microsoft Presidio (hybrid regex + NER reference implementation) —
  https://microsoft.github.io/presidio/
- PII redaction accuracy benchmark, regex vs NER vs hybrid —
  https://www.ertas.ai/blog/pii-redaction-accuracy-benchmark-regex-ner-llm
