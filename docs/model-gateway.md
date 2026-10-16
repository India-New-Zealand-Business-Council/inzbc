# Model gateway configuration and usage records

`services/api/model_gateway.py` is the single server-side completion and embeddings interface.
Existing callers continue to use `complete(prompt, source=...)`, and semantic retrieval / dedupe
callers (#63) use `embed(text, source=...)`; source refusal and configured redaction run before
provider access for both methods. No live credentials or runtime environment files are changed
by this implementation.

| Configuration name | Behavior |
|---|---|
| `SIP_MODEL_PROVIDER` | `openai` by default; the only other accepted value is `perplexity` (`embed()` requires `openai`) |
| `SIP_MODEL_NAME` | Existing OpenAI default remains; required explicitly for Perplexity |
| `SIP_EMBEDDING_MODEL_NAME` | Optional OpenAI embeddings model; defaults to `text-embedding-3-small` |
| `OPENAI_API_KEY` | Used only for OpenAI |
| `PERPLEXITY_API_KEY` | Used only for Perplexity; no fallback to the other provider/key |
| `DATABASE_URL` | When configured, usage records persist through the existing append-only audit service |
| `SIP_MODEL_INPUT_USD_PER_MILLION` | Optional operator-supplied input-token rate for an estimate |
| `SIP_MODEL_OUTPUT_USD_PER_MILLION` | Optional operator-supplied output-token rate for an estimate |
| `SIP_EMBEDDING_INPUT_USD_PER_MILLION` | Optional operator-supplied embedding input-token rate for an estimate |

Perplexity uses the existing OpenAI SDK against the fixed `https://api.perplexity.ai/v1` base
URL and the Responses interface, as documented in its
[compatibility guide](https://docs.perplexity.ai/docs/agent-api/openai-compatibility).
No provider tools are requested. Responses are sent with `store=False`; this controls response
retrieval and is not a claim about a provider's retention policy. Provider account/model access
must be configured by the account owner before live use.

The gateway has one retry, a 30-second SDK timeout, and SDK retries disabled so the retry count
does not multiply. Each completed invocation records provider, configured model, elapsed time,
attempt count, success/failure, token counts and cost basis. Missing or invalid usage is unknown,
not zero. Successful metadata does not include unknown billing from failed attempts.

`stream()` (#65) applies the same source refusal and redaction before returning, then yields
text deltas. It is never retried, because text may already have reached a reader. Closing it
closes the provider stream, and one usage record is written however it ends: success only after
a completed response with text. A stream abandoned mid-way usually has no token counts, so its
cost is unknown.

[OpenAI usage](https://developers.openai.com/api/docs/guides/token-counting) reports input and
output counts. A provider-reported USD total is retained where available; otherwise both
configured rates and both counts are required for a clearly labeled token-cost estimate.
No rates are guessed or hardcoded. Estimates are not invoices and do not model caching or tool
charges separately. Missing rates/counts leave cost unknown.

Usage logs contain no prompt, generated text, matched identifiers, API key, source URL or raw
provider error. Without a database, local usage is logged only; that is not durable audit
storage. With `DATABASE_URL`, `model.call` is appended to `audit_log` in its own transaction.
An audit failure prevents return of the result and does not retry the provider: an external
request cannot be rolled back or made free by retrying a database write.

Unit tests use injected clients and sinks, including failure/retry cases. CI exercises the
existing transactional audit mechanism against Postgres. No live provider smoke test or semantic
quality measurement is claimed. The unresolved staff-prose boundary under #303 still applies;
adding a second provider does not resolve or waive it.
