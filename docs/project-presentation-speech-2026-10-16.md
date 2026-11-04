# INZBC project presentation

**About five minutes. Read the paragraphs aloud. The headings are cues, not part of the speech.**

## 1. Introduction

Good morning. Today we are presenting our project for the India New Zealand Business Council,
or INZBC. Our team is Bhanu, Roshan and Paras.

Our project connects four main areas: a refreshed public website, trade intelligence,
an FTA Opportunity Explainer, and an AI Communications Assistant.

The aim is to help INZBC turn information into useful guidance and communications, while
keeping important decisions under human control.

## 2. The problem

INZBC works with information about trade, investment, policy and business opportunities.
The challenge is deciding which information matters, checking its sources, and presenting it
clearly to members.

Using AI alone would not solve that problem. AI can produce convincing mistakes. We therefore
needed a system that keeps track of evidence, review and approval, as well as generating useful
drafts.

## 3. What we built

The first area is the Strategic Intelligence Platform, which we call SIP. It supports a workflow
from collecting potential stories to assessing them, preparing a brief and recording human
review. It keeps an audit history so an operator can see who acted and what was approved.

The second area is the FTA Opportunity Explainer. It searches a curated collection of sourced
facts. It returns source-linked guidance and makes missing coverage visible. This part does not
ask an AI model to invent tariff answers.

The third area is the Communications Assistant. Staff provide a brief, and AI helps draft
content such as a newsletter section, an event announcement or a LinkedIn post. The result
still needs a named human reviewer.

The fourth area is the public website rebuild. Membership continues through Member Jungle,
rather than creating a second membership database.

## 4. How the technology works

Our backend uses Python and FastAPI, with PostgreSQL storing the platform records. The staff
interface uses React and TypeScript. We chose Python partly because it let us reuse the existing
collection engine and keep one backend language across the team.

For AI tasks, the platform's default model is OpenAI's GPT-4.1 mini. We use an existing model;
we have not trained our own.

All platform model requests go through one server-side gateway. It checks the declared input
source, applies the configured redaction policy, and records usage information. API keys stay
on the server.

The gateway has a thirty-second timeout and allows one retry. We do not explicitly set a
temperature or output-token limit in the current gateway. AI supports scoring, drafting and
quality assessment, but cannot grant approval or publish independently.

## 5. Ideas we developed

One useful idea was separating relevance from verification. A story can look important without
its claims being verified, so we treat those as different judgments.

Another improvement came from FTA searches. A broad word such as “exports” could outweigh the
product the user actually asked about. We improved the ranking and added an explicit warning
when only general guidance is available.

We also developed an advisory quality checker. It assesses whether a brief is relevant to New
Zealand, gives members something practical to do, supports its claims, and avoids exaggerated
urgency. Its scores help a human reviewer; they do not replace one.

## 6. Timeline and testing

The placement began in July. We started with discovery, requirements, source material and
architecture decisions. In August, we developed the API, database, interfaces and security
controls. In September, we brought the main modules into one application and fixed integration
problems by running the workflow end to end.

In October, we improved retrieval evaluation, dependency security, model-usage records and the
quality checker.

Our automated checks cover backend and frontend tests, security scanning, API contracts and
Docker builds. The known FTA evaluation set currently records perfect results, but we do not
claim perfect real-world accuracy. A separate question-set proposal reports eighty percent
top-result accuracy, which shows remaining weaknesses.

The live quality checker also passed eight synthetic test cases. That is useful evidence,
but it is not proof of performance on every real brief.

## 7. Current position and closing

The core application is built and tested, but production launch is not approved. Remaining work
includes deployment verification, further evaluation, integration tasks and completing the
handover walkthrough and recovery evidence.

Our main lesson is that reliable AI systems need more than a good prompt. They need clear data
boundaries, tests, traceable records and human responsibility.

That is the focus of our project: helping INZBC use information and AI through a controlled,
reviewable workflow. Thank you.

---

## Quick answers — only use these if asked

- **Model:** GPT-4.1 mini by default; configurable through `SIP_MODEL_NAME`.
- **Timeout/retries:** 30-second SDK timeout; one retry; no explicit temperature or output-token cap.
- **Database/backend/frontend:** PostgreSQL / Python and FastAPI / React and TypeScript.
- **FTA knowledge:** 23 corpus facts, 22 marked confirmed; current retrieval does not use an LLM.
- **AI quality test:** Eight synthetic cases passed; human QA remains required.
- **Team lanes:** Bhanu — technical lead and platform; Roshan — intelligence, data and FTA;
  Paras — frontend, product experience and website. Check worklogs for detailed attribution.
- **Costs:** Usage is recorded where available; no verified total running cost to quote.
- **Next steps:** Existing engineering tasks, verified deployment, acceptance evidence and handover.

Detailed evidence and limitations: [full reference briefing](project-presentation-brief-2026-10-16.md).
