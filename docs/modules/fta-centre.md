# Module — FTA Implementation Centre

Owner: Roshan · Status: spec (source corpus started) · Public overview + member depth + the Explainer.

## Purpose
Turn the NZ–India FTA into exporter/importer decisions: a sourced knowledge base plus a guided
Opportunity Explainer. A sourced information service, **not** an unsupervised chatbot.

## What it answers
What changed under the FTA? Which tariff applies to my product? When does the concession begin?
Does my product qualify (rules of origin)? What documentation? Which Indian state/buyer/partner?
What barriers remain? What next step?

## Source order (required)
1. Official NZ treaty/government · 2. Government of India + customs · 3. Official tariff / rules-of-origin /
implementation · 4. Approved regulator/standards · 5. Approved INZBC analysis (clearly marked as interpretation).
See [../fta-source-corpus.md](../fta-source-corpus.md).

## Every material answer contains
Answer date, source date/effective date, citation, jurisdiction, assumptions, next step, disclaimer
where professional advice may be required. Status line: the FTA is signed but **not yet in force**.

## Content lifecycle
Each item: owner, source, version, approval status, effective date, review date, superseded status,
correction history.

## Dependencies
Bhanu's API for the Explainer service; official source access; INZBC sectors-in-scope + disclaimer +
legal/technical review process.

## Definition of done
Source hierarchy implemented; citations + effective dates visible; stale-content detection;
correction/withdrawal tested; representative sector questions evaluated; unsupported-answer behaviour
tested (routes to INZBC, never guesses).
