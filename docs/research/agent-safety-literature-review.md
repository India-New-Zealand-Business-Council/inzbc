# Literature review: safe agent coordination under human approval

**Author:** Bhanu Gupta. **Status:** Annotated draft, 24 Oct 2026. Prepared with AI assistance.
Every source was checked against its arXiv, Crossref, publisher or OWASP record on 24 Oct 2026
(section 6), and claims are limited to what those records state. Studio 6 objective 2.1, applied
in 2.2 through `apps/sip/core/eval/` and
[agent-safety-baseline.md](agent-safety-baseline.md).

## 1. Introduction: the question

INZBC's daily intelligence run (SIP-184) has steps a machine can do and decisions only a person
may make. Locking a 24-hour window, recording source checks, scoring and drafting are mechanical.
QA sign-off, the CEO decision and distribution are not. The coordinator agent (#62) uses a
language model to plan the mechanical steps. This review asks four things the design depends on:

1. How should an agent hand decisions to people, and what does "human in the loop" require?
2. Can a tool-using agent be constrained so it cannot take a forbidden action, and where should
   the constraint live?
3. How do untrusted inputs (collected news items) attack an agent, and which defences hold?
4. Can a language model judge the quality of a brief, and how should its judgement be checked
   against people?

## 2. Human-in-the-loop agents

Amershi et al. (2019) set out 18 design guidelines for human-AI interaction, evaluated with 49
design practitioners against 20 AI products. Shneiderman (2020) argues against a single dial
between human and machine control. High human control and high automation can coexist, and the
design question is which actions need which. Both frame the human role as designed in, not
bolted on.

**What this means for #62.** The agent automates the steps where it is useful and is structurally
unable to take the decisions reserved for people. That is Shneiderman's high-control,
high-automation quadrant, built as code rather than as a policy the model is asked to follow.

## 3. Guardrails for LLM tool use

ReAct (Yao et al., 2022) interleaves reasoning with actions, and Toolformer (Schick et al., 2023)
trains a model to decide which tool to call and with what arguments. Both make the model the
decider of actions. Guardrail toolkits add controls around that. NeMo Guardrails (Rebedea et al.,
2023) adds programmable "rails" that are independent of the model, and Llama Guard (Inan et al.,
2023) classifies inputs and outputs with a second model. ToolEmu (Ruan et al., 2023) shows why
tool use needs testing: even its safest agent failed in 23.9% of its high-stakes test cases.
OWASP's 2025 Top 10 for LLM applications names this risk "Excessive Agency" (LLM06).

**What this means for #62.** A classifier guardrail is itself a model and can be wrong. For an
action that must never happen, such as crossing a human gate, the safer place for the rule is
deterministic code that the model's output passes through. That code consists of:
- seven allowed tools
- strict argument schemas that reject unknown fields
- a state machine that refuses illegal or human-gated transitions

The model proposes; the code decides.

## 4. Prompt injection

Perez and Ribeiro (2022) show goal hijacking and prompt leaking with simple handcrafted inputs.
Greshake et al. (2023) extend this to **indirect** injection: instructions planted in data the
application retrieves, which then "control how and if other APIs are called". That is the SIP
case: every collected headline and summary is attacker-reachable. Defences divide in two.
Spotlighting (Hines et al., 2024) marks untrusted input so the model can tell sources apart,
cutting attack success from over 50% to under 2% in its experiments. That is a large reduction
but not zero. CaMeL (Debenedetti et al., 2025) takes the other route: it extracts control flow
from the trusted query, so untrusted data "can never impact the program flow". AgentDojo
(Debenedetti et al., 2024) is a benchmark that shows attacks breaking some security properties
but not all.

**What this means for #62.** The agent does both. Untrusted run data is placed in a JSON block the
prompt labels as data, which is a spotlighting-style signal. More importantly, as in CaMeL, the
injected text cannot reach the decisions that matter. Even a model that fully obeys an injection
can only propose one of seven tools, and the gates are not among them. The baseline tests that
directly: in three prompt-injection attacks the model obeys the injection, and all three are
blocked.

## 5. LLM-as-judge evaluation

Zheng et al. (2023) report that strong judges such as GPT-4 reach over 80% agreement with human
preferences, about the level humans reach with each other. They also document position,
verbosity and self-enhancement biases. G-Eval (Liu et al., 2023) reports a Spearman correlation
of 0.514 with humans on summarisation and warns that LLM evaluators may favour LLM-written text.
Agreement between two raters on categories should be corrected for chance, which is what Cohen's
kappa does (Cohen, 1960).

**What this means for #64.** A judge with known biases and imperfect agreement can advise, but it
should not approve. The quality judge returns scores only. `needs_revision` is computed in code,
the verdict schema has no approval field, and the human QA gate is unchanged. Its agreement with
people is measured as raw agreement plus kappa against an independent reviewer, not assumed from
published figures.

## 6. Audit and replay

Schneier and Kelsey (1999) describe logs kept on a machine that may be compromised, and a cheap
method that makes entries written before the compromise impossible to read or to modify
undetectably. Their threat is the one the baseline found. A log that records a human decision
without binding it to its author can have a decision forged into it.

## 7. Comparison

| Approach | Where the rule lives | Can a compliant model break it? | Used in #62 to #64 |
|---|---|---|---|
| Prompt instructions only | In the prompt | Yes (Perez & Ribeiro; Greshake et al.) | As a first layer only |
| Spotlighting / data marking | In the prompt format | Rarely (Hines et al.: under 2%) | Yes: untrusted JSON block |
| Classifier guardrail | A second model | Sometimes (it is a model) | No |
| Programmable rails | Runtime, model-independent | Not for covered paths | Partly: strict schemas |
| Control/data-flow separation | Code around the model | No, by construction (CaMeL) | Yes: tool allow-list, state machine, verification gate |
| Advisory judge | Separate scorer, no authority | Not applicable: it cannot act | Yes (#64) |
| Signed, hash-chained audit | Storage and the log format | Not without the key | Planned (W6–W7) |

## 8. What this means for the project

1. Keep every irreversible decision out of the model's reach, in code. Measured: 48 of 48 attacks
   blocked, and each control is proven necessary by a knockout.
2. Treat collected content as untrusted data, never instructions, and test with a model that
   obeys the injection.
3. Keep the judge advisory, and measure it against an independent human reviewer before relying
   on it.
4. Close the forged-decision gap by signing human decisions and chaining the log (Schneier &
   Kelsey), then re-measure.

## 9. Annotated bibliography

Each annotation has four parts: reference, summary, evaluation and application to INZBC.

**1. Amershi et al. (2019).**
*Reference.* Amershi, S., Weld, D., Vorvoreanu, M., Fourney, A., Nushi, B., Collisson, P., Suh,
J., Iqbal, S., Bennett, P. N., Inkpen, K., Teevan, J., Kikin-Gil, R., & Horvitz, E. (2019).
Guidelines for human-AI interaction. In *Proceedings of the 2019 CHI Conference on Human Factors
in Computing Systems* (pp. 1-13). https://doi.org/10.1145/3290605.3300233
*Summary.* Proposes 18 general design guidelines for human-AI interaction, validated over several
rounds, including a study in which 49 design practitioners tested them against 20 AI products.
*Evaluation.* Peer-reviewed and widely cited. It is about interaction design, not agent security,
so it says what people need from an AI system rather than how to enforce it.
*Application.* Supports making the agent's hand-off points explicit to the people involved. The
SIP screens name which run is being acted on and state that the agent stops at QA.

**2. Shneiderman (2020).**
*Reference.* Shneiderman, B. (2020). Human-centered artificial intelligence: Reliable, safe &
trustworthy. *International Journal of Human–Computer Interaction, 36*(6), 495-504.
https://doi.org/10.1080/10447318.2020.1741118
*Summary.* Presents a framework in which high human control and high automation can coexist, and
which clarifies when full human or full computer control is needed.
*Evaluation.* A conceptual framework from a leading HCI author, not an empirical study. Its value
is the vocabulary for placing each step.
*Application.* Places SIP-184: mechanical steps are automated, and QA, CEO decision and
distribution stay fully human. The agent automates up to the QA gate and no further.

**3. Yao et al. (2022).**
*Reference.* Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022).
*ReAct: Synergizing reasoning and acting in language models* (arXiv:2210.03629). arXiv.
https://doi.org/10.48550/arXiv.2210.03629
*Summary.* Has a model interleave reasoning traces with actions against external tools, improving
results on question answering, fact checking and two interactive decision tasks.
*Evaluation.* The arXiv record marks v3 as the ICLR camera-ready. Influential, but it makes the
model the decider of actions, and safety is not its subject.
*Application.* #62 uses the same propose-act loop, but each proposal is a single allow-listed tool
call that code accepts or refuses, rather than free action.

**4. Schick et al. (2023).**
*Reference.* Schick, T., Dwivedi-Yu, J., Dessì, R., Raileanu, R., Lomeli, M., Zettlemoyer, L.,
Cancedda, N., & Scialom, T. (2023). *Toolformer: Language models can teach themselves to use
tools* (arXiv:2302.04761). arXiv. https://doi.org/10.48550/arXiv.2302.04761
*Summary.* Trains a model, self-supervised, to decide which API to call, when, with what
arguments, and how to use the result.
*Evaluation.* Shows tool choice can be learned, which makes it a capability paper. It does not
address constraining which tools may be used.
*Application.* The contrast motivates #62's design: tool choice is the model's, and tool
permission is the code's. Only seven tools exist, and none can cross a human gate.

**5. Rebedea et al. (2023).**
*Reference.* Rebedea, T., Dinu, R., Sreedhar, M., Parisien, C., & Cohen, J. (2023). *NeMo
Guardrails: A toolkit for controllable and safe LLM applications with programmable rails*
(arXiv:2310.10501). arXiv. https://doi.org/10.48550/arXiv.2310.10501
*Summary.* An open-source toolkit that adds programmable, model-independent rails controlling what
an LLM application says and which dialogue paths it follows.
*Evaluation.* EMNLP 2023 demo track. The authors' results are described as initial. Aimed at
conversational systems rather than state-changing agents.
*Application.* Shares #62's principle that rules should sit outside the model. #62 goes further
for its critical path: the rails are the state machine itself, not a layer the model passes
through.

**6. Inan et al. (2023).**
*Reference.* Inan, H., Upasani, K., Chi, J., Rungta, R., Iyer, K., Mao, Y., Tontchev, M., Hu,
Q., Fuller, B., Testuggine, D., & Khabsa, M. (2023). *Llama Guard: LLM-based input-output
safeguard for human-AI conversations* (arXiv:2312.06674). arXiv.
https://doi.org/10.48550/arXiv.2312.06674
*Summary.* An instruction-tuned Llama 2 7B model that classifies prompts and responses against a
safety risk taxonomy, matching or beating existing moderation tools on public benchmarks.
*Evaluation.* Strong for content moderation, but it is a probabilistic classifier.
*Application.* Not adopted. A classifier that is right most of the time is the wrong tool for
"never cross a human gate". It could still screen collected content, a separate decision.

**7. Ruan et al. (2023).**
*Reference.* Ruan, Y., Dong, H., Wang, A., Pitis, S., Zhou, Y., Ba, J., Dubois, Y., Maddison, C.
J., & Hashimoto, T. (2023). *Identifying the risks of LM agents with an LM-emulated sandbox*
(arXiv:2309.15817). arXiv. https://doi.org/10.48550/arXiv.2309.15817
*Summary.* ToolEmu emulates tools with a model to test agents across 36 high-stakes tools and 144
cases. Even the safest agent failed 23.9% of the time.
*Evaluation.* Human evaluation found 68.8% of the failures it identified would be real, so its
numbers are estimates.
*Application.* Motivates testing #62 adversarially rather than trusting the design. The baseline
does this with a deterministic suite, and ToolEmu suggests how to scale it.

**8. Perez and Ribeiro (2022).**
*Reference.* Perez, F., & Ribeiro, I. (2022). *Ignore previous prompt: Attack techniques for
language models* (arXiv:2211.09527). arXiv. https://doi.org/10.48550/arXiv.2211.09527
*Summary.* Introduces PromptInject and shows goal hijacking and prompt leaking against GPT-3 with
simple handcrafted inputs.
*Evaluation.* An early, workshop-level paper (NeurIPS 2022 ML Safety Workshop). Its value is
showing how cheap the attacks are.
*Application.* Why prompt wording alone cannot be the control. The agent's prompt tells it to
ignore instructions in run data, but the baseline assumes the model may not.

**9. Greshake et al. (2023).**
*Reference.* Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023).
Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect
prompt injection. In *Proceedings of the 16th ACM Workshop on Artificial Intelligence and
Security* (pp. 79-90). https://doi.org/10.1145/3605764.3623985
*Summary.* Shows indirect prompt injection, where instructions are planted in retrieved data,
against real systems, and argues these applications blur data and instructions.
*Evaluation.* Peer-reviewed. It defines the threat class that applies to any system reading the
open web.
*Application.* The SIP collector reads news from 112 sources, so every headline is an injection
channel. Three baseline attacks put the injection in collected content.

**10. Hines et al. (2024).**
*Reference.* Hines, K., Lopez, G., Hall, M., Zarfati, F., Zunger, Y., & Kiciman, E. (2024).
*Defending against indirect prompt injection attacks with spotlighting* (arXiv:2403.14720).
arXiv. https://doi.org/10.48550/arXiv.2403.14720
*Summary.* Transforms untrusted input so the model can tell where text came from. Attack success
fell from over 50% to under 2% with GPT models.
*Evaluation.* Practical and cheap, but under 2% is not zero, and the paper evaluates GPT-family
models only.
*Application.* #62's untrusted JSON block is a spotlighting-style signal, used as the first
layer. The guarantee does not depend on it.

**11. Debenedetti et al. (2024).**
*Reference.* Debenedetti, E., Zhang, J., Balunović, M., Beurer-Kellner, L., Fischer, M., &
Tramèr, F. (2024). *AgentDojo: A dynamic environment to evaluate prompt injection attacks and
defenses for LLM agents* (arXiv:2406.13352). arXiv. https://doi.org/10.48550/arXiv.2406.13352
*Summary.* An extensible benchmark with 97 tasks and 629 security test cases. Current models fail
many tasks, and attacks break some security properties but not all.
*Evaluation.* A benchmark rather than a defence, built to be extended with new attacks.
*Application.* A model for growing the 48-attack suite systematically, and a reminder that a
fixed suite gives a lower bound only.

**12. Debenedetti et al. (2025).**
*Reference.* Debenedetti, E., Shumailov, I., Fan, T., Hayes, J., Carlini, N., Fabian, D., Kern,
C., Shi, C., Terzis, A., & Tramèr, F. (2025). *Defeating prompt injections by design*
(arXiv:2503.18813). arXiv. https://doi.org/10.48550/arXiv.2503.18813
*Summary.* CaMeL extracts control and data flow from the trusted query, so untrusted data "can
never impact the program flow". It solves 77% of AgentDojo tasks with provable security, against
84% undefended.
*Evaluation.* A preprint, but the closest design to #62. Its cost (77% against 84%) is a fair
warning.
*Application.* #62 has the same structure: the program flow is the SIP-184 state machine, and
nothing a model reads can add a transition. The baseline's knockouts show which control carries
each guarantee.

**13. OWASP (2025).**
*Reference.* OWASP Foundation. (2025). *OWASP top 10 for LLM applications 2025*.
https://genai.owasp.org/llm-top-10/
*Summary.* Lists the ten main risks for LLM applications, including LLM01 Prompt Injection and
LLM06 Excessive Agency.
*Evaluation.* An industry consensus list, not research. Useful as a checklist and shared
vocabulary.
*Application.* #62 addresses LLM01 by separating data from control and LLM06 with the
seven-tool allow-list. The baseline gives evidence for both.

**14. Zheng et al. (2023).**
*Reference.* Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li,
Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). *Judging LLM-as-a-judge
with MT-Bench and Chatbot Arena* (arXiv:2306.05685). arXiv.
https://doi.org/10.48550/arXiv.2306.05685
*Summary.* Strong LLM judges reach over 80% agreement with human preferences, about the
human-human level. Position, verbosity and self-enhancement biases are documented.
*Evaluation.* NeurIPS 2023 Datasets and Benchmarks. The agreement is on chat-assistant
preferences, not on domain rubrics like SIP-050.
*Application.* Sets a reference point, not an expectation. #64's agreement has to be measured on
INZBC's own rubric and briefs, and the judge stays advisory.

**15. Liu et al. (2023).**
*Reference.* Liu, Y., Iter, D., Xu, Y., Wang, S., Xu, R., & Zhu, C. (2023). *G-Eval: NLG
evaluation using GPT-4 with better human alignment* (arXiv:2303.16634). arXiv.
https://doi.org/10.48550/arXiv.2303.16634
*Summary.* Uses chain-of-thought and form-filling for LLM evaluation, reaching a Spearman
correlation of 0.514 with humans on summarisation, and warns of a bias towards LLM-written text.
*Evaluation.* An improvement over earlier metrics, but 0.514 is modest, and the bias matters when
the drafts themselves are model-written.
*Application.* The SIP brief drafts may be model-assisted, so the judge's agreement must be
checked against a human, never taken from the literature.

**16. Cohen (1960).**
*Reference.* Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and
Psychological Measurement, 20*(1), 37-46. https://doi.org/10.1177/001316446002000104
*Summary.* Introduces the coefficient now known as Cohen's kappa, for agreement between two raters
on nominal categories.
*Evaluation.* The standard reference for chance-corrected agreement. With few cases, as in an
8-case golden set, kappa is unstable.
*Application.* `judge_agreement.py` reports kappa next to raw agreement, and the baseline says to
read raw agreement first at this size.

**17. Schneier and Kelsey (1999).**
*Reference.* Schneier, B., & Kelsey, J. (1999). Secure audit logs to support computer forensics.
*ACM Transactions on Information and System Security, 2*(2), 159-176.
https://doi.org/10.1145/317087.317089
*Summary.* For logs kept on a machine that may be compromised, gives a cheap method that makes
entries written before the compromise impossible to read and impossible to modify or destroy
undetectably.
*Evaluation.* An older but foundational paper. Its threat model is the one the replay baseline
exposes.
*Application.* Basis for the planned W6–W7 change: bind each human decision to its author and
chain the log, then re-measure forged-decision detection.

## References

Amershi, S., Weld, D., Vorvoreanu, M., Fourney, A., Nushi, B., Collisson, P., Suh, J., Iqbal, S.,
Bennett, P. N., Inkpen, K., Teevan, J., Kikin-Gil, R., & Horvitz, E. (2019). Guidelines for
human-AI interaction. In *Proceedings of the 2019 CHI Conference on Human Factors in Computing
Systems* (pp. 1-13). https://doi.org/10.1145/3290605.3300233

Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological
Measurement, 20*(1), 37-46. https://doi.org/10.1177/001316446002000104

Debenedetti, E., Shumailov, I., Fan, T., Hayes, J., Carlini, N., Fabian, D., Kern, C., Shi, C.,
Terzis, A., & Tramèr, F. (2025). *Defeating prompt injections by design* (arXiv:2503.18813).
arXiv. https://doi.org/10.48550/arXiv.2503.18813

Debenedetti, E., Zhang, J., Balunović, M., Beurer-Kellner, L., Fischer, M., & Tramèr, F. (2024).
*AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM
agents* (arXiv:2406.13352). arXiv. https://doi.org/10.48550/arXiv.2406.13352

Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). Not what
you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt
injection. In *Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security*
(pp. 79-90). https://doi.org/10.1145/3605764.3623985

Hines, K., Lopez, G., Hall, M., Zarfati, F., Zunger, Y., & Kiciman, E. (2024). *Defending against
indirect prompt injection attacks with spotlighting* (arXiv:2403.14720). arXiv.
https://doi.org/10.48550/arXiv.2403.14720

Inan, H., Upasani, K., Chi, J., Rungta, R., Iyer, K., Mao, Y., Tontchev, M., Hu, Q., Fuller, B.,
Testuggine, D., & Khabsa, M. (2023). *Llama Guard: LLM-based input-output safeguard for human-AI
conversations* (arXiv:2312.06674). arXiv. https://doi.org/10.48550/arXiv.2312.06674

Liu, Y., Iter, D., Xu, Y., Wang, S., Xu, R., & Zhu, C. (2023). *G-Eval: NLG evaluation using GPT-4
with better human alignment* (arXiv:2303.16634). arXiv. https://doi.org/10.48550/arXiv.2303.16634

OWASP Foundation. (2025). *OWASP top 10 for LLM applications 2025*.
https://genai.owasp.org/llm-top-10/

Perez, F., & Ribeiro, I. (2022). *Ignore previous prompt: Attack techniques for language models*
(arXiv:2211.09527). arXiv. https://doi.org/10.48550/arXiv.2211.09527

Rebedea, T., Dinu, R., Sreedhar, M., Parisien, C., & Cohen, J. (2023). *NeMo Guardrails: A
toolkit for controllable and safe LLM applications with programmable rails* (arXiv:2310.10501).
arXiv. https://doi.org/10.48550/arXiv.2310.10501

Ruan, Y., Dong, H., Wang, A., Pitis, S., Zhou, Y., Ba, J., Dubois, Y., Maddison, C. J., &
Hashimoto, T. (2023). *Identifying the risks of LM agents with an LM-emulated sandbox*
(arXiv:2309.15817). arXiv. https://doi.org/10.48550/arXiv.2309.15817

Schick, T., Dwivedi-Yu, J., Dessì, R., Raileanu, R., Lomeli, M., Zettlemoyer, L., Cancedda, N., &
Scialom, T. (2023). *Toolformer: Language models can teach themselves to use tools*
(arXiv:2302.04761). arXiv. https://doi.org/10.48550/arXiv.2302.04761

Schneier, B., & Kelsey, J. (1999). Secure audit logs to support computer forensics. *ACM
Transactions on Information and System Security, 2*(2), 159-176.
https://doi.org/10.1145/317087.317089

Shneiderman, B. (2020). Human-centered artificial intelligence: Reliable, safe & trustworthy.
*International Journal of Human–Computer Interaction, 36*(6), 495-504.
https://doi.org/10.1080/10447318.2020.1741118

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022). *ReAct:
Synergizing reasoning and acting in language models* (arXiv:2210.03629). arXiv.
https://doi.org/10.48550/arXiv.2210.03629

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D.,
Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). *Judging LLM-as-a-judge with
MT-Bench and Chatbot Arena* (arXiv:2306.05685). arXiv. https://doi.org/10.48550/arXiv.2306.05685

## 10. Check against the originals, 24 Oct 2026

| # | Record opened | What matched | What was not checked |
|---|---|---|---|
| 1 | Crossref `10.1145/3290605.3300233`; Microsoft Research publication page | Title, 13 authors, CHI 2019, pp. 1-13. Abstract: 18 guidelines, 49 practitioners, 20 products | Paper body |
| 2 | Crossref `10.1080/10447318.2020.1741118`; arXiv:2002.04087 abstract | Title, author, IJHCI 36(6), 495-504. Abstract: high control plus high automation | Paper body |
| 3 | arXiv API, 2210.03629 | Title, 7 authors, abstract. Comment: v3 is the ICLR camera-ready | Paper body; ICLR proceedings page |
| 4 | arXiv API, 2302.04761 | Title, 8 authors, abstract | Paper body |
| 5 | arXiv API, 2310.10501 | Title, 5 authors, abstract. Comment: EMNLP 2023 demo track | Paper body |
| 6 | arXiv API, 2312.06674 | Title, 11 authors, abstract | Paper body |
| 7 | arXiv API, 2309.15817 | Title, 9 authors, abstract: 36 tools, 144 cases, 23.9%, 68.8% | Paper body |
| 8 | arXiv API, 2211.09527 | Title, 2 authors, abstract. Comment: NeurIPS 2022 ML Safety Workshop | Paper body |
| 9 | Crossref `10.1145/3605764.3623985`; arXiv API, 2302.12173 | Title, 6 authors, AISec '23, pp. 79-90, abstract | Paper body |
| 10 | arXiv API, 2403.14720 | Title, 6 authors, abstract: over 50% to under 2% | Paper body |
| 11 | arXiv API, 2406.13352 | Title, 6 authors, abstract: 97 tasks, 629 cases | Paper body |
| 12 | arXiv API, 2503.18813 | Title, 10 authors, abstract: 77% against 84% | Paper body |
| 13 | genai.owasp.org/llm-top-10 | 2025 list, LLM01 Prompt Injection, LLM06 Excessive Agency | Individual risk pages |
| 14 | arXiv API, 2306.05685 | Title, 13 authors, abstract: over 80% agreement, biases. Comment: NeurIPS 2023 D&B | Paper body |
| 15 | arXiv API, 2303.16634 | Title, 6 authors, abstract: Spearman 0.514, LLM-text bias | Paper body |
| 16 | Crossref `10.1177/001316446002000104` | Title, author, EPM 20(1), 37-46 | No abstract in Crossref; the claim is the standard definition of kappa |
| 17 | Crossref `10.1145/317087.317089`, including the abstract | Title, 2 authors, TISSEC 2(2), 159-176, abstract | Paper body |
