# Literature review: surfacing agent trust and reasoning in the UI

**Author:** Paras (one DOI added by Bhanu Gupta, noted below). **Status:** Annotated draft, 28 Oct 2026. Prepared with AI assistance. Every
source was checked against its arXiv, ACM DL, ACL Anthology, Springer, IEEE or Zenodo record on 28
Oct 2026, and claims are limited to what those records state. VisTrails DOI added and its record
checked by Bhanu Gupta, 28 Oct 2026. Studio 6's course requirement to show
research beyond frontend/backend work, applied directly to `apps/sip/ui`'s two agent surfaces:
`AgentRehearsalPanel.tsx` (the coordinator agent's rehearsal trail) and `PlatformAssistant.tsx`
(the read-only chat agent).

This is a different angle on the same underlying system Bhanu's
[agent-safety-literature-review.md](agent-safety-literature-review.md) covers. His review asks how
the agent should be *constrained* (guardrails, tool-use limits, human gates built as code). This
one asks a narrower, UI-level question his doesn't: once the agent has acted, how should the
*interface* represent what it did and how sure anyone should be about it, to the person reading
the screen. Neither review repeats the other's sources.

## 1. Introduction: the question

Both components already show a human a record of something an AI did: the rehearsal panel shows a
recorded trail of tool steps with hash-chain/replay results and a seal status; the assistant
shows an answer plus what it looked up and a disclaimer. **As reviewed**, an unsealed or
key-unavailable trail was also labelled green "Trail verified" by the UI, despite no verified
signature. [PR #494](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/494)
proposes a neutral unverified state; until it is merged, the UI claim is stronger than the proof. Four questions
this review asks, each tied to a specific choice already made in that code:

1. What do general guidelines for human-AI interaction say about explaining what a system did and
   how confident to be in it?
2. Does showing a confidence/trust signal next to an AI output actually calibrate a reader's trust
   correctly, or can it backfire?
3. What happens to a reader's trust after they see the AI get something wrong, once badges and
   explanations are already part of the picture?
4. Is there a more specific precedent for showing a step-by-step audit trail of automated actions,
   closer to what the rehearsal panel already does?

## 2. Human-AI interaction guidelines

Amershi et al. (2019), "Guidelines for Human-AI Interaction," CHI 2019 (DOI
[10.1145/3290605.3300233](https://doi.org/10.1145/3290605.3300233)), set out 18 guidelines
developed and validated through a multi-step process by Microsoft's Aether, Microsoft Research and
Office teams, grouped into four categories by when they apply: initially, during interaction, when
the system is wrong, and over time. I could not get the exact wording of all 18 from a public page
without the paper itself — the project page shows them only as an image — so I'm citing the
category structure and theme, not inventing specific guideline text I haven't verified.

**What this means for the two components.** The rehearsal panel displays server-computed
chain/seal/replay diagnostics when *provenance or replay* fails. This is distinct from an
AI answer being **factually false but well-formed**: an intact, signed trail can still contain
a mistaken claim. Likewise the assistant's 503/422 handling reports **service configuration or
request-validation failure**, not detection of a plausible but false answer. Neither UI currently
contains a factual-error acknowledgement/correction workflow. The rehearsal panel offers
expand/collapse and refresh, **not** a dismiss, acknowledge or remember action; remembered
acknowledgement is a possible future design requiring its own safety review. An integrity failure
must remain visible even if someone acknowledges it.

## 3. Confidence signals don't guarantee better decisions

Zhang, Liao and Bellamy (2020), "Effect of Confidence and Explanation on Accuracy and Trust
Calibration in AI-Assisted Decision Making," FAT* 2020 (DOI
[10.1145/3351095.3372852](https://doi.org/10.1145/3351095.3372852)), ran two experiments on
AI-assisted decisions where a human and an AI had comparable accuracy. Showing a confidence score
helped people calibrate *trust* to match the AI's real accuracy. But calibrated trust alone did not
reliably improve the *decision* — that also depended on whether the human brought knowledge the AI
lacked. The paper separately flags problems with using local, per-prediction explanations for this
purpose, without fully resolving them.

**What this means for the two components.** These indicators are provenance diagnostics, **not
AI confidence or factual correctness**. The backend returns whether the chain is intact, whether
replay is exact, and whether a cryptographic seal is `valid`, `invalid`, `unsealed` or
`key-not-configured`. At the 28 October code-review baseline, the UI showed the green
"Trail verified" badge for all seal states except `invalid` when chain/replay passed — so green
**did not** mean all three checks had succeeded. [Issue #493](https://github.com/India-New-Zealand-Business-Council/inzbc/issues/493)
and [PR #494](https://github.com/India-New-Zealand-Business-Council/inzbc/pull/494)
track the correction: green only for `valid` seal + exact replay + intact chain, neutral
for unsealed/key-unavailable, red on failed checks. Even a fully verified trail does not
prove the *content* of the agent's brief is accurate or suitable to distribute.

## 4. Explanations can cause the wrong kind of agreement

Naiseh, Al-Thani, Jiang and Ali (2021), "Explainable recommendation: when design meets trust
calibration," *World Wide Web* 24(5), pp. 1857–1884 (DOI
[10.1007/s11280-021-00916-0](https://doi.org/10.1007/s11280-021-00916-0)), ran a 16-participant
think-aloud study and two co-design sessions. They found that engaging with an explanation can
itself produce miscalibrated agreement or disagreement — a plausible-looking explanation can earn
trust it hasn't actually demonstrated. Their five design principles: design for engagement,
challenge habitual actions, guide attention, add friction before acting on an explanation, and
support training/learning.

**What this means for the two components.** The rehearsal panel's step list (`tool_steps`, each
with `reason`, `outcome`, `detail`) is exactly the kind of explanation this paper warns about — a
plausible, readable narrative that could earn trust the underlying trail hasn't actually verified.
The panel uses server-returned verification metadata, rather than deriving verification from
the narrative text, so a glib-sounding `reason` cannot legitimately establish cryptographic
provenance. However, the pre-#494 green label overstated that metadata when the seal was absent
or unverifiable. A further "guide attention" gap remains: refused and accepted steps share
the same list container styling, distinguished mainly by a small text label ("Refused" /
"Accepted"), so the point of refusal does not visually stand out.

## 5. Trust drops fast after a wrong answer, and recovers slowly

Dhuliawala, Zouhar, El-Assady and Sachan (2023), "A Diachronic Perspective on User Trust in AI
under Uncertainty," EMNLP 2023, pp. 5567–5580 (ACL Anthology
[2023.emnlp-main.339](https://aclanthology.org/2023.emnlp-main.339)), used a betting game to show
that a handful of confidently wrong answers lowers a user's trust and the team's joint performance,
and that trust recovers slowly afterward. Users trusted the system less after a confidently wrong
answer than after an unconfidently correct one, even when the payoff was the same.

**What this means for the two components.** Directly relevant to the assistant: it has no
confidence signal at all today, only a disclaimer line ("AI-generated and advisory."). This paper's
finding suggests that's probably the safer default for a system that can't yet back a confidence
number with anything real — a wrong answer presented without false confidence is the better failure
mode this research describes, not a gap to fix by adding a confidence score the assistant has no
honest way to compute.

## 6. A closer precedent for the rehearsal panel's step list

Bavoil, Callahan, Crossno, Freire, Scheidegger, Silva and Vo (2005), "VisTrails: Enabling
Interactive Multiple-View Visualizations," IEEE Visualization 2005, pp. 135–142 (DOI
[10.1109/VISUAL.2005.1532788](https://doi.org/10.1109/VISUAL.2005.1532788)), describe a
provenance system that records every change a user (or an automated process) makes to a
visualization pipeline and presents it as a directed graph, so a past state can be reproduced and
inspected. It's the oldest and most established precedent I found for showing a step-by-step
record of automated changes for later verification, rather than just a final result.

Separately, Narayan (2026), "Designing the Action Receipt: Ensuring Transparency and Auditability
in Autonomous Multi-Agent Workflows," Zenodo, DOI
[10.5281/zenodo.21305058](https://doi.org/10.5281/zenodo.21305058), proposes a structured "action
receipt" for what an agent did on a user's behalf, and names open problems: information overload,
receipts an adversarial agent could falsify, and privacy risk from retaining detailed logs. **Flag,
not a citation to lean on:** this is a self-deposited Zenodo record with no stated peer review,
published July 2026 — a lead worth reading, not an authority. I'm naming it because its open-problem
list (information overload especially) is a real, concrete risk the rehearsal panel's full step
list already has no mitigation for.

## Findings applied to this week's UI

1. **The badge is a verification-of-trail signal, not a verified-*fact* signal** (§3).
   At the 28 October review baseline, green could be shown without a verified cryptographic seal.
   #493/#494 track the needed three-state correction. Even once corrected, it will not verify
   the truth of the model's narrative or its recommendations.
2. **The step a rehearsal refused at doesn't visually stand out** (§4) — same list styling as every
   accepted step, distinguished only by a small coloured word.
3. **The assistant's lack of a confidence score is probably correct, not a gap** (§5) — adding one
   without a real basis for it risks the "confidently wrong" failure mode this research specifically
   found most damaging to trust.
4. **Neither component has a remembered acknowledgement/correction mechanism** (§2).
   The rehearsal panel does not offer dismissal of failed trails at all. Any future acknowledgement
   must preserve failure visibility and cannot imply that a false answer or invalid seal was fixed.

## What this means for Thursday

The seal-status correction (#493/#494) is the immediate prerequisite for trust communication:
the UI must not claim a verified signature where none was checked. An independent subsequent UI
improvement is to give refused steps more visual weight without changing their audit content.
Neither task is a substitute for independently reviewing generated factual claims or a human
release decision.
