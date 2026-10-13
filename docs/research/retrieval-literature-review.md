# Literature review: retrieval for governed AI

**Author:** Roshan Aryal. **Status:** Draft, started 13 Oct 2026. Annotated bibliography due W4
(26 to 30 Oct). Studio 6 objective 2.1, applied in 2.2 through `apps/fta/eval/`.

Every reference below must be checked against the original before it is cited in the final
version. Mark each one as checked in the bibliography table.

## 1. Introduction: why retrieval matters for INZBC

The FTA Explainer answers member questions about the NZ-India Free Trade Agreement. It may only
say what a confirmed, cited corpus entry says, and it must send anything it cannot match to INZBC
instead of guessing (`docs/modules/fta-centre.md`). So the quality of the whole service depends
on one step: finding the right entry for the question.

Today that step is a weighted keyword match with IDF weighting over 23 entries
(`apps/fta/explainer.py`). The baseline eval on 13 Oct (`apps/fta/eval/results/baseline.json`)
shows where it works and where it does not:

| Question type | n | hit@1 | MRR |
|---|---|---|---|
| Exact wording | 18 | 1.000 | 1.000 |
| Multi-term | 8 | 0.750 | 0.875 |
| Synonyms the corpus does not use | 10 | 0.200 | 0.200 |
| Must return no match | 6 | no-match accuracy 1.000 | |

A member who asks about "lamb" or "international students" gets nothing, even though the corpus
covers sheepmeat and student visas. This review asks three questions:

1. Which retrieval methods could close the synonym gap, and what do they cost?
2. How do you ground an answer in retrieved text and evaluate it?
3. How do you keep provenance, so every answer can be traced to a verified source?

## 2. Key theories and technologies

### 2.1 Lexical retrieval: TF-IDF and BM25

Lexical methods score a document by the query terms it shares, weighted by how rare each term
is. BM25 (Robertson & Zaragoza, 2009) adds two corrections to plain TF-IDF: term frequency
saturates, so the tenth repeat of a word adds little, and long documents are normalised so they
do not win on length alone. Manning et al. (2008) cover the TF-IDF and vector-space model the
current Explainer is built on.

The strength is that lexical retrieval is transparent and cheap, and a score can be explained
term by term. The weakness is the vocabulary mismatch problem: no shared word means no match.
That is the synonym result in the baseline.

### 2.2 Dense retrieval: embeddings

Dense retrieval encodes the question and each passage as vectors and ranks by similarity.
Karpukhin et al. (2020) trained a BERT dual encoder on question-passage pairs (Dense Passage
Retrieval, DPR) and beat BM25 on top-20 passage accuracy across several open-domain QA sets.
Because the match is on meaning, "lamb" can land near "sheepmeat".

The limit is generalisation. BEIR (Thakur et al., 2021) tested retrievers zero-shot across 18
datasets and found BM25 a strong baseline that many dense models failed to beat outside the
domain they were trained on. INZBC has no training pairs, so any embedding model would be used
zero-shot, which is exactly the setting where BEIR found dense retrieval least reliable.

### 2.3 Hybrid retrieval

Hybrid retrieval runs a lexical and a dense retriever and fuses the two rankings. Reciprocal Rank
Fusion (Cormack et al., 2009) combines lists using rank alone, so the two score scales do not
need calibrating. Bruch et al. (2023) compared fusion functions and found that a convex
combination of normalised scores can beat RRF when some tuning data exists.

For INZBC the attraction is that exact-wording questions keep their lexical match, which scores
1.000 today, while synonyms gain a second route in.

### 2.4 Retrieval-augmented generation (RAG)

Lewis et al. (2020) joined a dense retriever to a sequence-to-sequence generator, so the model
writes its answer conditioned on retrieved passages rather than only on what it memorised. They
reported more specific and more factual output than a generator alone on knowledge-intensive
tasks. Gao et al. (2023) survey the field since then and group systems into naive, advanced and
modular RAG. Retrieval quality is the main lever on answer quality.

The Explainer is deliberately not RAG in the generation sense. It returns the corpus entry
itself, with no model writing prose. The retrieval half of this research applies directly. The
generation half applies to the Comms Assistant and SIP briefs, not to the FTA answers.

### 2.5 Evaluating retrieval and RAG

Ranked retrieval is measured with hit@k and mean reciprocal rank (Manning et al., 2008), which
is what `apps/fta/eval/` reports. RAGAS (Es et al., 2023) proposes reference-free scores for a
whole RAG pipeline: faithfulness (is the answer supported by the retrieved context), answer
relevance, and context relevance. These are judged by a language model.

For the FTA corpus a hand-labelled question set is affordable and more trustworthy than a model
judge. RAGAS-style faithfulness is more relevant to issue #64 (LLM-as-judge for briefs).

### 2.6 Provenance and governance

W3C PROV-DM (Moreau & Missier, 2013) models provenance as entities, the activities that
generated or used them, and the agents responsible. It provides relations such as
`wasDerivedFrom` and `wasAttributedTo`. The NIST AI Risk Management Framework (NIST, 2023)
organises AI risk work into Govern, Map, Measure and Manage. It lists "valid and reliable" and
"accountable and transparent" among the marks of trustworthy AI.

Each corpus entry already carries a citation, a source tier and a verified date. That is
provenance in all but name. PROV-DM gives a standard vocabulary for it. NIST's Measure function
is what a committed eval set and a before vs after score provide.

## 3. Comparison and evaluation

| Approach | How it works | Strength | Weakness | Fit for the 23 FTA entries |
|---|---|---|---|---|
| Keyword TF-IDF (today) | Shared terms weighted by rarity | Transparent, no dependencies, exact wording 1.000 | No match without a shared word. Synonyms 0.200 | Good floor. Keep it |
| BM25 | TF-IDF with saturation and length normalisation | Strong zero-shot baseline (BEIR) | Same vocabulary gap | Little gain. Entries are short, so length normalisation barely matters |
| BM25 plus synonym list | Expand the query from a curated term map | Explainable, no model call, cheap to test | The list has to be maintained by hand, and misses terms nobody listed | Strong. A small corpus makes a curated list realistic |
| Dense embeddings | Rank by vector similarity | Matches meaning, so it handles synonyms | Zero-shot reliability (BEIR). Needs a model, which may cross the model data boundary in ADR-0006 | Possible, but must not lose an exact or no-match result |
| Hybrid (RRF) | Fuse lexical and dense rankings | Keeps exact matches and adds semantic recall | Two systems to run. A similarity cut-off is needed or no-match questions start returning answers | Best candidate if embeddings are approved under #63 |

The deciding risk for INZBC is not the miss but the false answer. A dense retriever always
returns its nearest neighbour, even for "steel" or "pharmaceuticals", which the corpus does not
cover. Today those return no match and route to INZBC (no-match accuracy 1.000). Any change has
to keep that, which means a similarity threshold, tuned and checked on the six no-match
questions.

## 4. What this means for the project

1. **Measure first.** Done: 42 questions, baseline committed (#382).
2. **Cheapest change first:** a curated synonym map inside `apps/fta`, with no model call. It is
   expected to fix most of the ten synonym questions. Re-run the eval.
3. **Then embeddings under #63**, if Bhanu agrees and the model data boundary allows it. The
   design would be hybrid with RRF, plus a similarity threshold so no-match questions stay
   unanswered.
4. **Report all variants in one table** (keyword, keyword plus synonyms, embeddings, hybrid), by
   question type, in W7.
5. **What does not apply:** training a DPR model (no labelled pairs, and 23 entries do not
   justify it), and RAG generation for FTA answers (the Explainer must quote the corpus, not
   paraphrase it).

## 5. Annotated bibliography

Each entry needs about 150 words in four parts: reference, summary, evaluation, application to
INZBC. The summaries above are first notes. Expand each into a full annotation by 30 Oct.

| # | Source | Type | Checked against original | Annotation done |
|---|---|---|---|---|
| 1 | Robertson & Zaragoza (2009) | Peer-reviewed | | |
| 2 | Manning, Raghavan & Schütze (2008) | Textbook | | |
| 3 | Karpukhin et al. (2020) | Peer-reviewed | | |
| 4 | Thakur et al. (2021) | Peer-reviewed | | |
| 5 | Cormack, Clarke & Büttcher (2009) | Peer-reviewed | | |
| 6 | Bruch, Gai & Ingber (2023) | Peer-reviewed | | |
| 7 | Lewis et al. (2020) | Peer-reviewed | | |
| 8 | Gao et al. (2023) | Preprint survey | | |
| 9 | Es et al. (2023) | Preprint | | |
| 10 | Moreau & Missier (2013) | Standard | | |
| 11 | NIST (2023) | Framework | | |

Target is 12 or more. One more peer-reviewed source on query expansion or synonym handling would
support step 2 of section 4.

## References

Bruch, S., Gai, S., & Ingber, A. (2023). An analysis of fusion functions for hybrid retrieval.
*ACM Transactions on Information Systems, 42*(1), 1-35. https://doi.org/10.1145/3596512

Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion outperforms
Condorcet and individual rank learning methods. In *Proceedings of the 32nd International ACM
SIGIR Conference on Research and Development in Information Retrieval* (pp. 758-759).
https://doi.org/10.1145/1571941.1572114

Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2023). *RAGAS: Automated evaluation of
retrieval augmented generation* (arXiv:2309.15217). arXiv. https://doi.org/10.48550/arXiv.2309.15217

Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., & Wang, H.
(2023). *Retrieval-augmented generation for large language models: A survey* (arXiv:2312.10997).
arXiv. https://doi.org/10.48550/arXiv.2312.10997

Karpukhin, V., Oguz, B., Min, S., Lewis, P., Wu, L., Edunov, S., Chen, D., & Yih, W. (2020).
Dense passage retrieval for open-domain question answering. In *Proceedings of the 2020
Conference on Empirical Methods in Natural Language Processing* (pp. 6769-6781).
https://doi.org/10.18653/v1/2020.emnlp-main.550

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M.,
Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for
knowledge-intensive NLP tasks. In *Advances in Neural Information Processing Systems 33*
(pp. 9459-9474).

Manning, C. D., Raghavan, P., & Schütze, H. (2008). *Introduction to information retrieval*.
Cambridge University Press.

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model* (W3C Recommendation).
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

National Institute of Standards and Technology. (2023). *Artificial intelligence risk management
framework (AI RMF 1.0)* (NIST AI 100-1). https://doi.org/10.6028/NIST.AI.100-1

Robertson, S., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond.
*Foundations and Trends in Information Retrieval, 3*(4), 333-389.
https://doi.org/10.1561/1500000019

Thakur, N., Reimers, N., Rücklé, A., Srivastava, A., & Gurevych, I. (2021). BEIR: A
heterogeneous benchmark for zero-shot evaluation of information retrieval models. In
*Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks*.
