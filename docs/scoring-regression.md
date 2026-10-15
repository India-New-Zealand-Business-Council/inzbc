# SIP-050 offline scoring regression

Issue #38 is covered by `apps/sip/core/tests/test_scoring_regression.py` and the versioned
`data/scoring-regression.json` beside it. Run:

```sh
uv run python -m pytest apps/sip/core/tests/test_scoring_regression.py -q
```

The existing CI Python job includes these tests through `pytest apps services`.
No API key, database, provider request or real article/member data is needed.

The fixtures contain synthetic article fields and manually authored model-output strings.
They replay low, medium, high and critical recommendations; malformed JSON, duplicate keys,
wrong types, missing/extra fields, invalid enums and out-of-range scores; and article text
containing braces and instruction-like payloads. A valid High/Critical recommendation is also
passed through the real assessment gate: with no human verification, no pipeline write occurs.
The model cannot supply verification or inclusion fields through this contract.

The SHA-256 baseline pins the rendered scoring prompt for the synthetic base candidate.
Changing the prompt requires reviewing the changed instructions and updating the fixture hash
deliberately in the same PR. Expected recommendations and refusal outcomes remain versioned.

This is a parser, prompt-assembly and safety-contract regression suite. A fake gateway does not
show whether a real model obeys injected instructions or scores an article accurately. It does
show that candidate braces remain data and that replayed malicious output cannot widen the
schema or bypass the verification gate. Live semantic calibration remains separate work under
#39; no fabricated model measurements or human approvals are recorded here.
