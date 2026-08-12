# Redaction policy

The mechanism is built and enforced, and **the policy is now approved**:
`config/redaction-policy.json`. What still gates a real model call is deployment, not the decision:
`REDACTION_POLICY_PATH` must point at the file, and where it does not, every call refuses.

`docs/sip/README.md` makes redaction ahead of every external model call a non-negotiable. What
counts as confidential is a business rule, and `PROJECT-RULES.md` says not to fill an unresolved rule with
an assumption. So `services/api/redaction.py` ships the machinery and treats a missing policy as a
refusal rather than as permission.


## What this layer cannot do

These rules match formatted identifiers. They do not catch a person's name, job title, employer, or
anything else carried in ordinary prose, and no set of regexes will. This input passes through
untouched:

    Delegation lead: Priya Sharma, Chief Executive, Koru Exports Ltd

The policy document previously pointed at review-before-publication as the remaining control for
this. That is wrong, and the error mattered: review happens after the payload has already reached
the provider. Publication review cannot undo a disclosure.

The control for prose is not to send it, and that control now exists:
`services/api/prompt_boundary.py` (#223). Every model call names where its text came from, and a
member record, CRM note, Board paper or private message is refused at the gateway before a policy
is read. Prompts built from structured records go through `minimise()`, which keeps only
allowlisted fields, so a name or job title is dropped by never being asked for rather than by being
recognised.

**That does not promote this layer.** Redaction remains defence in depth for formatted identifiers,
and it must still not be described as making it safe to send member data to a model. Approving the
policy does not make it so.

**One case has no structural control**, and it is worth knowing which: the Comms Assistant brief is
free text a staff member types, so there is no record to minimise. What bounds it is the operator
being told not to paste member details and told why, with redaction catching the identifiers it can
match. That is weaker than the structured path, and it is the reason the operator guide says so
plainly.

Two evasions are defended because they are cheap to defend: a full-width `＠` homoglyph, and a
number split across a line break. Others are not. Policy authorship remains a trusted operation.

## The approved policy

`config/redaction-policy.json` carries the Executive Sponsor's approval, taken on 9 August 2026 and
relayed by the Technical Lead. It covers email, New Zealand and India phone numbers, IRD and NZBN,
GSTIN and PAN, passport numbers, payment cards, New Zealand bank accounts, member identifiers,
street addresses and credential shapes.

The rules are unchanged from the proposed set that was put to him. Approval was of **the rules as
written**, so editing one needs its own approval rather than inheriting this one.

**The written instrument is still owed** (#37). What is recorded is that the decision was taken, by
whom and when. The convention in this repository is that the Executive Sponsor's authority is
exercised in writing, so this is an accurate record of a decision rather than the instrument
itself, and it is worth closing with one email.

**Approval does not deploy it.** `REDACTION_POLICY_PATH` must point at the file in each
environment, and where it is unset every model call still refuses. That default stays, in
production as much as anywhere: an environment nobody has configured must fail closed rather than
send unredacted text.

Never put real member data in this file. The examples use `example.test` addresses and invented
numbers on purpose, and the file is committed to the repository.

`services/api/tests/test_redaction_policy.py` holds both ends still: sensitive shapes must not
survive, and real trade content must. Over-redaction is the quieter failure. A brief that reaches a
member with its tariff line masked is useless, and nobody will report it as a redaction bug.

### To change a rule

1. Read it. The rules are regexes with a literal replacement, chosen so a non-engineer can check
   what each does. If a rule is not readable, it is not approvable, and that is a defect in the
   rule.
2. Decide what is missing. The approved set covers shapes we could anticipate. INZBC knows its own
   data, and anything it considers confidential that is not on the list will not be redacted.
3. Get the change approved on its own terms, and record who approved it and when. The point of this
   control is that somebody owns the answer to what counts as confidential.


## How it behaves today

Every call goes through `ModelGateway.complete()`, which redacts before it reaches a provider. Not
per caller: a control each caller has to remember is a control one caller will forget.

With no `REDACTION_POLICY_PATH` set, `complete()` raises `RedactionNotConfiguredError` and the
provider is never contacted. An empty rule list is refused too, so "we have not decided yet" and
"nothing is confidential" cannot be the same configuration. Redaction runs *before* the API key is
checked, so a missing policy surfaces even on a machine that could not have called out anyway.

`GatewayResult.redaction_counts` records which rules fired and how often, by name. It never carries
the matched text, because an audit trail that quotes what it redacted has not redacted it.

## What INZBC owes

A policy file. The shape is deliberately plain so someone who is not a programmer can read and
approve it:

```json
{
  "rules": [
    { "name": "member-email", "pattern": "[\\w.+-]+@[\\w-]+\\.[\\w.]+",
      "replacement": "[redacted:email]",
      "example": "contact sunil@example.test about the brief" }
  ]
}
```

The decisions behind it, none of which are ours:

1. **What categories are confidential.** Member names and contact details, Board papers and
   deliberations, commercial terms, unpublished intelligence, anything else.
2. **Mask or drop.** A masked value keeps the shape of the text and so keeps the prompt coherent; a
   dropped one is safer and may make the prompt useless. This can differ per category.
3. **What happens to a payload that is mostly confidential.** If redaction removes the substance,
   the right answer may be not to call a model at all rather than to send a hollowed-out prompt.
4. **Who approves changes to the policy**, and whether a change is itself an auditable event.

Until those are answered the file does not exist, and nothing sends. That is the intended state,
not a gap.

## Deliberate limits

Regex is a blunt instrument. It will not catch a member's name written in prose, or a Board
decision described without naming it. This layer removes the categories that can be matched
mechanically; it is not a guarantee that nothing sensitive reaches a provider, and should not be
described to INZBC as one. The named-reviewer gate before publication remains the control that
catches what this cannot.

Every rule matches the **original** payload, not the previous rule's output, and overlapping
matches are merged so the union is redacted. Both matter, and an earlier version got both wrong: a
rule that masked `Member ID:` first left `Member ID: 123456` no longer matching the rule that
would have removed the number, and a rule matching another rule's replacement token could put the
original value back. An overlap can now only ever remove more text, never less.

Every rule carries an `example`: a sample of the thing it is meant to catch. At load, the rule is
run against its own example, and a rule that removes nothing from it is refused.

This exists because the earlier check was too narrow. It rejected a pattern that matched the empty
string at position 0, which catches `x*` but not `(?=.*secret)`. That second one is a pure
assertion: it loads cleanly, and every match it produces is zero-length, so the redactor skips all
of them and nothing is removed. The count is honestly zero, so the audit trail does not lie, but
whoever wrote the rule believes there is a control where there is none. A pattern with a typo in it
fails in exactly the same silent way, and that is the likelier case: `Member ID\s+\d+` looks right
and never fires against `Member ID: 123456`.

Whether a rule can ever match is undecidable in general, so it is not inferred. The rule states
what it should catch and has to prove it on that sample before the policy will load.

Replacements are literal. Backreference syntax is refused at load, because a rule replacing a match
with `\1` would emit the original value while the audit trail recorded a successful redaction.

Payloads are capped at 200,000 characters. Python's regex engine has no match timeout, so a
pathological pattern against unbounded input can hang a worker; roughly 31 characters is enough
with the wrong rule. The cap removes the unbounded case but does not make a bad rule safe. **Policy
authorship is a trusted operation**: whoever writes the file can write a rule that hangs the
gateway, so it belongs with the people who already hold production configuration.

## Related

- Issue #37, this work.
- Issue #53, Comms Assistant service side. Blocked on the policy, not on the mechanism.
- Issue #65, streaming Comms API. Same.
- `services/api/tests/test_redaction.py` covers the fail-closed paths, including that a caller
  cannot reach a provider without a policy.
