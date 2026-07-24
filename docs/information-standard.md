# INZBC Information Standard

Approved wording supplied by Sunil Kaushal (CEO), 24 July 2026. This document is the
controlling reference; code (`apps/fta/standards.py`) mirrors it — update here first, then
mirror, the same relationship `apps/fta/corpus.py` has to `docs/fta-source-corpus.md`.

Three parts: the publication standard (for documents and web pages), the AI standard (for
Claude/ChatGPT-style responses and the future website assistant), and the Information
Confidence Standard (a per-response rating that every AI answer carries).

## 1. Publication standard (documents and web pages)

> The India New Zealand Business Council (INZBC) is committed to providing accurate, practical
> and evidence-based information to support trade, investment and business engagement between
> New Zealand and India.
>
> This information has been prepared using official government publications, recognised
> industry sources and other trusted references available at the time of publication.
>
> While every reasonable effort has been made to ensure the accuracy of this information,
> legislation, regulations, tariffs, policies and commercial conditions may change without
> notice.
>
> This material is provided as general business information only and should not be regarded as
> legal, taxation, customs, immigration, financial or other professional advice. Businesses
> should obtain independent professional advice before making significant commercial or
> investment decisions.
>
> If you require assistance interpreting this information or would like support with your New
> Zealand–India business activities, the INZBC team is available to help.

## 2. AI Information Standard (AI responses)

> This response has been prepared using official government publications and trusted industry
> sources maintained by the India New Zealand Business Council (INZBC). While every effort is
> made to provide accurate and current information, regulatory requirements and commercial
> conditions can change. This response is intended as general business guidance and should not
> be relied upon as legal, taxation, customs, immigration or financial advice. Where an answer
> cannot be verified from authoritative sources, INZBC will indicate this rather than
> speculate. For advice specific to your business or transaction, please contact INZBC or an
> appropriately qualified professional adviser.

The sentence "Where an answer cannot be verified from authoritative sources, INZBC will
indicate this rather than speculate" is the operative commitment: it matches the fail-closed
behaviour already built into the Explainer (`[]` / escalate-to-INZBC instead of a guess) and
the SIP verification gate (unverified High/Critical assessments refused).

## 3. Information Confidence Standard

Every AI response carries a confidence rating, not just a disclaimer:

| Confidence | Meaning |
|---|---|
| High | Verified using official government or treaty sources. |
| Medium | Verified using reputable industry or recognised secondary sources; users should confirm current requirements. |
| Low | Limited authoritative information is available; the response is based on the best available evidence and should be independently verified. |
| Action Required | INZBC recommends contacting the relevant government agency or seeking professional advice before proceeding. |

## Application map

- **FTA Explainer** (`apps/fta`): every answer carries the AI Information Standard as its
  disclaimer plus a confidence rating derived from the cited source's tier (Tier 1 official →
  High; Tier 2 industry/secondary → Medium). Unconfirmed corpus entries remain suppressed
  (fail closed). A no-match response routes to INZBC — surface it as **Action Required**.
- **SIP briefs / Comms Assistant / website assistant**: adopt the same wording and rating when
  those surfaces are built; the publication standard applies to site pages and documents.
