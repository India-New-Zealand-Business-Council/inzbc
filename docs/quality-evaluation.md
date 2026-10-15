# Advisory brief-quality evaluation (#64)

`apps/sip/core/quality.py` evaluates a draft against four explicit dimensions drawn from
[SIP-050 v1.1](sip/launch/SIP-050_master_prompt_v1.1.md): NZ relevance (§11–12, QA-07), member
actionability (§12/18, QA-11), evidence support (§14, QA-08), and signal discipline (§13/16–17,
QA-09/10). It covers these quality checks, not all twenty SIP-188 operational controls.

Every score must be a JSON integer from 0 to 5 with a nonblank reason. Missing/extra fields,
duplicate keys, booleans, numeric strings, out-of-range scores and invented approval fields are
refused. `needs_revision` is computed in code if any dimension scores below 3. The verdict has no
state transition, verification, approval or publication method. Human QA remains mandatory.

Brief and evidence are bounded, JSON-encoded untrusted data beneath a fixed rubric. Embedded
instructions cannot change the parser or grant authority. Prompting reduces injection risk; it
cannot guarantee the model will assign honest scores. Evidence excerpts are context, not proof
that a source is authentic. The caller must explicitly declare the combined input's true
`PromptSource`; prohibited origins are refused and the gateway applies redaction before sending.

## Regression checks

The eight cases in `apps/sip/core/tests/data/quality-golden.json` are **hand-authored synthetic
fixtures**, with expected score ranges. They are not client-approved briefs, an observed quality
benchmark, or evidence of real-world accuracy. Cases cover supported guidance, unsupported tariff
claims, irrelevant news, vague actions, urgency inflation, duplication and an instruction attack.

```powershell
uv run python scripts/eval_quality.py
uv run python scripts/eval_quality.py --live --report quality-eval-report.json
```

The first command validates the corpus and pinned rubric fingerprint without a model call; CI
runs it and the refusal/regression tests on every PR. A rubric edit requires explicit golden-label
review and fingerprint update. This alone does **not** measure model quality.

The second command performs the actual model evaluation through the gateway. Any golden-bound
failure, provider/configuration error or malformed verdict exits nonzero. The manual
**Advisory brief quality regression** Actions workflow runs it for the selected model using the
existing repository OpenAI secret and approved redaction policy. It saves case IDs, scores,
revision flags, model and rubric fingerprint; it does not save model prose or credentials.

Run that workflow on the reviewed prompt/model candidate before accepting a quality change.
Live inference is not automatically run on every PR, and the manual job is not a required branch
check. Without a successful live report, no semantic-quality result is claimed. The corpus is
capped at 20 gateway calls (currently eight); the gateway may retry each provider call once.
This evaluates synthetic public fixtures only, never client acceptance documents or private drafts.
