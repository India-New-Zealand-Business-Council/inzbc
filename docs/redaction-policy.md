# Redaction policy

The mechanism is built and enforced. **The policy is not written, and until it is, no model call
can be made at all.** That is deliberate.

`docs/sip/README.md` makes redaction ahead of every external model call a non-negotiable. What
counts as confidential is a business rule, and `CLAUDE.md` says not to fill an unresolved rule with
an assumption. So `services/api/redaction.py` ships the machinery and treats a missing policy as a
refusal rather than as permission.

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
    { "name": "member-email", "pattern": "[\\w.+-]+@[\\w-]+\\.[\\w.]+", "replacement": "[redacted:email]" }
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

Rules apply in file order, so a broader rule placed later cannot undo a narrower one placed
earlier. Every rule runs on every payload; there is no short-circuit, because two categories can
appear in the same text.

## Related

- Issue #37, this work.
- Issue #53, Comms Assistant service side. Blocked on the policy, not on the mechanism.
- Issue #65, streaming Comms API. Same.
- `services/api/tests/test_redaction.py` covers the fail-closed paths, including that a caller
  cannot reach a provider without a policy.
